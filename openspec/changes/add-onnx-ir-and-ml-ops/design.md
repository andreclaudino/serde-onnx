# Design: ONNX IR, ai.onnx.ml ops e framework de exportação (Fase 1)

Ver proposal.md para motivação e escopo; specs/ para contratos de comportamento.

## Context

Projeto do zero (sem código além de `Cargo.toml` vazio, edition 2024). Consumidor principal imediato: sciencekit (scikit-learn-like em Rust), cujos modelos fitted precisam virar `.onnx` e cujos pipelines clássicos precisam compor com ops do `ai.onnx.ml`. Duas fases: esta cobre IR genérica (sem subgrafos funcionais), codec protobuf, ops `ai.onnx.ml` tipados + subconjunto mínimo de `ai.onnx` e o framework de exportação; a fase 2 completa com os ops NN de `ai.onnx`, subgrafos e FunctionProto.

## Goals / Non-Goals

**Goals**
- IR em memória completa para modelos de inferência do domínio clássico, construível e validável programaticamente.
- Round-trip fiel encode/decode protobuf para os recursos no escopo.
- Exportação de modelo fitted como algo trivial (trait + builder + macro derive para o caso simples).
- Decode com reconhecimento semântico de ops (grafo "reconhecível"), retendo o resto fielmente.

**Non-Goals**
- Executor/avaliador de grafos ONNX (não rodamos nada; export/decode apenas).
- Suporte a todas as versões de opset/IR (fixamos um alvo; rejeição explícita fora do alvo).
- Converting modelos NN completos (`ai.onnx` completo) — fase 2.
- Adaptador específico com sciencekit (fica no lado do consumidor; aqui só a trait genérica).
- Inferência de shape estática avançada (shapes vêm do que o exporter declara; validação básica apenas).

## Decisions

### D1: IR própria vs. usar os tipos prost gerados como IR
**Decisão**: IR própria (structs/enums idiomáticos) como representação canônica; os tipos prost são uma camada de transporte, convertidos de/para a IR.

- Alternativa A (usar protos gerados direto como "IR"): rejeitada — proto gerado usa `Option`, bytes crus, oneofs verbosos e não exprime enums de atributos/ops tipados; propagaria a feiura de protobuf para todo consumidor e daí `serde-onnx` seria só um wrapper de prost.
- Alternativa B (serde custom em cima do protobuf wire): rejeitada — duplicaria todo o trabalho de um codec que já existe.

### D2: Codegen protobuf com prost + prost-build a partir dos `.proto` oficiais
**Decisão**: `prost-build` gera os tipos de transporte de `onnx.proto3`, `onnx-operators.proto3`, `onnx-ml.proto3`, `onnx-operators-ml.proto3` do repositório onnx/onnx (vendados no repo para builds herméticos e atualização deliberada).

- Atualização de versões dos protos vira um passo manual (script + diff), nunca automático — dados de modelo ≠ dados de aplicação.
- `ElemType`/`AttributeType`/`TensorProto.DataCase` são mapeados para enums dessa lib (não se vaza o tipos do prost no API público).

### D3: Workspace de duas crates com features `export`/`import`
**Decisão**: workspace com `serde-onnx` (biblioteca) e `serde-onnx-macros` (proc-macro do derive, dependência opcional gated pela feature `export`). Módulos `ir`, `ml`, `numeric` (tipos numéricos) e `proto` (codec) sempre presentes.

- `export` = trait `ToOnnx` + `GraphBuilder` + `export_model` + re-export da macro.
- `import` = decode para grafo semântico com pattern matching (o codec básico proto→IR fica sempre presente; `import` é a camada de reconhecimento).
- Proc-macros não podem morar no mesmo crate da biblioteca; fica aqui a única divisão física inevitável.

### D4: Numéricos — enum tipado de dados + trait Scalar sealed
**Decisão** (conforme explorado): `TensorData` enum com variantes tipadas (F32..U64, Bool, String, F16/Bf16 como bits u16, cru para tipos exóticos int4/fp8), `ElemType` declarado explicitamente (não derivado de variantes sozinho para tipos exóticos), trait `Scalar` sealed (f32, f64, i8..i64, u8..u64, bool) com `ELEM_TYPE` associado, acesso `as_slice::<T>` (exato) e `to_vec::<T>` (checked via `num-traits::NumCast`).
- Atributos ficam f32/i64 conforme o spec; tentativa de valor fora de range → erro explícito.
- `half` para f16/bf16; bytes LE explícitos na fronteira prost (nunca `as` silencioso).

### D5: Ops tipados: structs + associação estática em lugar de registry dinâmico
**Decisão**: cada op `ai.onnx.ml` é uma struct com campos de hiperparâmetros; exposição comum por uma trait local (`OnnxOp`) comassociated `OP_TYPE`, `DOMAIN` e seleção por match em decode:
```rust
match (node.domain.as_str(), node.op_type.as_str()) {
    ("ai.onnx.ml", "Scaler") => Scaler::from_node(&node)? ,
    ("ai.onnx.ml", "TreeEnsembleClassifier") => TreeEnsembleClassifier::from_node(&node)?,
    ... // fallback: NodePayload::Raw(proto retido)
}
```
- Alternativa (registry/table genérica via inventory/linkme): rejeitada para fase 1 — match é simples, zero deps mágicas, e a lista de ops é pequena e estável.
- Opset alvo fixado (const): `ai.onnx` v. alvo + `ai.onnx.ml` v. alvo (ver tarefas; aprox. opset 21 / ml v5 — confirmar na implementação contra os protos vendados).

### D6: NodePayload como enum reconhecido/raw
**Decisão**: no path de import, `payload: NodePayload }` com variantes por domínio suportado (`Ml(Scaler)` etc.) e `Raw { proto: retido fielmente }`. Exporters tipados constroem nós com `NodePayload::Ml(...)` diretamente (o enum é o mesmo nos dois sentidos — é o que torna o round-trip simétrico). Nesta fase as variantes do enum de "payload" cobrem ml + subconjunto ai.onnx; genéricas para o resto chegam com a fase 2 via `Unknown`/`Raw`.

### D7: Derive macro mínima — mapa direto campo→atributo
**Decisão**: `#[derive(OnnxExport)]` + `#[onnx(op, domain, name?, ty)]` por campo gera impl de ToOnnx que emite um nó único, mapeando campos a atributos por nome; sem suporte a initializers/multi-nós na macro (esses casos ficam na impl manual da trait — o caminho feliz para sciencekit).
- A macro é "pão de ló": gera código simples, dá mensagem de erro clara para anotações inválidas; não tenta cobrir composição de pipeline.

### D8: Validação em export_model e no decode
**Decisão**: `export_model` roda validação estrutural da IR (SSA, definições de valores, shapes de I/O do grafo principal) e só então serializa. Decode marca recursos fora do escopo (subgrafos), mas não bloqueia; rejeita apenas protobuf inválido/versões não suportadas.

### D9: Nomes de valores e builder
**Decisão**: GraphBuilder gera nomes de outputs de nós automaticamente (counter + sufixo do op, ex. `node_3_Scaler_out`), verificando colisão; inputs/initializers nomeados explicitamente pelo exporter; nomes de dimensões simbólicas permitidos (Dim::Param) para assinatura (ex. `N`, `F`).

## Riscos / Trade-offs

- [Ops parcialmente cobertos] → Raw retém tudo; nenhum dado é descartado no decode; participantes sabem o que suportam pelos erros claros de from_node.
- [Versionamento de opsets muda semântica de ops entre versões] → opset alvo fixado; decode rejeita opsets acima do suportado com erro claro; suporte a múltiplas versões fica para fases futuras, op a op.
- [Protex vendado pode ficar outdated vs upstream] → atualização manual com diff e changelog; nunca automática via build script remoto.
- [f16/bf16/fp8 em Rust são limitados] → f16/bf16 via `half`; fp8/int4 ficam como bytes crus com dtype marcado (correto: não inventamos precisão que não existe).
- [u64 em atributo Int] → erro explícito; documentado no spec (spec ONNX não tem u64 attr).

## Open Questions

- Versão exata do opset alvo (confirmar contra os protos vendados na implementação; provável `ai.onnx` 21 + `ai.onnx.ml` 5, o mais recente estável suportado pelos protos).
- Feature `validation` separada vs. dentro de `export`/`import` (inclinação: validação estrutural sempre presente, é barata).
