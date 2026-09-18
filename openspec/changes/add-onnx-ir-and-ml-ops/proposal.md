# Proposal: ONNX IR, ai.onnx.ml ops e framework de exportação (Fase 1)

## Why

Não existe em Rust uma biblioteca que faça round-trip completo de modelos clássicos de ML (scalers, árvores, regressões lineares, SVMs) com ONNX. Modelos fitted (ex.: os do sciencekit) não podem ser exportados para `.onnx`, e modelos `.onnx` do domínio `ai.onnx.ml` não podem ser decodificados num grafo semântico reconhecível (ensembles, transformadores, tensores tipados) para conversão a outros formatos. Este change estabelece a fundação: a IR em memória, o codec protobuf, e o framework genérico de exportação — fase 1 de duas (a fase 2 completa com os ops de rede neural do domínio `ai.onnx`).

## What Changes

- **Nova IR em memória** fiel ao ONNX IR spec (Model → Graph → Node → Attribute/Tensor), sem subgrafos funcionais nesta fase (o enum de atributos reserva a variante `Graph`, mas decode/encode de subgrafos fica para a fase 2).
- **Codec protobuf** via `prost` com codegen dos `.proto` oficiais do onnx (onnx.proto3, onnx-operators.proto3, onnx-ml.proto3, onnx-operators-ml.proto3), fixando suporte a IR version ≤ atual e opset alvo.
- **Workspace de duas crates**: `serde-onnx` (biblioteca principal) + `serde-onnx-macros` (proc-macro do derive). Features: `export` (trait `ToOnnx`, `GraphBuilder`, re-export da macro) e `import` (decode de `.onnx` para IR com pattern matching para ops tipados). Módulos base (`ir`, `ml`, `proto`) sempre presentes.
- **Representação numérica segura**: `TensorData` como enum de variantes tipadas (F32/F64/I8..I64/U8..U64/Bool/String/F16/Bf16 + bytes crus para tipos exóticos), trait `Scalar` sealed mapeando tipos Rust → `ElemType` ONNX, acesso tipado com `as_slice` (exato) e `to_vec` (conversão checked, sem perda silenciosa). Atributos restritos a f32/i64 conforme o spec ONNX.
- **Ops `ai.onnx.ml` tipados** (~40 ops): structs Rust com hiperparâmetros tipados, cada um com `to_nodes()` (export) e `from_node()` (import), incluindo `Scaler`, `LinearClassifier`, `LinearRegressor`, `TreeEnsembleClassifier`, `TreeEnsembleRegressor`, `SVMClassifier`, `SVMRegressor`, `Imputer`, `Normalizer`, `OneHotEncoder`, `LabelEncoder`, `DictVectorizer`, `FeatureVectorizer`, `ZipMap`, etc.
- **Subconjunto mínimo de ops `ai.onnx`** necessários para pipelines clássicos: `Cast`, `Reshape`, `Concat`, `Gather`, `Identity` (como nós tipados; o restante fica como `NodePayload::Raw` retido fielmente).
- **Framework de exportação genérico** (feature `export`): trait `ToOnnx`, `GraphBuilder` (acumula nós, initializers, inputs/outputs tipados, declara opsets), função `export_model` de topo, e derive macro `#[derive(OnnxExport)]` com atributos `#[onnx(op = ..., domain = ..., attr = ..., ty = ...)]` para structs cujos campos mapeiam diretamente para atributos de um único nó.
- **Decode de `.onnx`** (feature `import`): arquivo → `Model` IR genérico → nós com payload reconhecido viram `NodePayload::Ml(op tipado)`; desconhecidos ficam `NodePayload::Raw(NodeProto)` retidos sem perda.
- **Validação**: testes de round-trip (export → encode → decode → comparação), incluindo o caso real do `SKStandardScalerModel` documentado como exemplo de integração; verificação de conformidade contra `onnx.checker` (Python) documentada como teste opcional/manual.

## Capabilities

### New Capabilities

- `onnx-ir`: Modelo em memória do grafo ONNX (Model, Graph, Node, Attribute, Tensor, TypeProto, ValueType, Dim) com semântica de SSA, namespaces de nomes, variadic/optional inputs e validação estrutural básica.
- `onnx-numeric-types`: Representação segura de tipos numéricos ONNX em tensores e atributos: enum `TensorData` tipado, trait `Scalar` sealed, conversões explícitas sem perda silenciosa, little-endian explícito na fronteira proto.
- `onnx-proto-codec`: Codec binário protobuf (`prost`) entre a IR em memória e arquivos `.onnx`, cobrindo ModelProto/GraphProto/NodeProto/AttributeProto/TensorProto (incl. external data e raw_data LE).
- `onnx-ml-ops`: Ops tipados do domínio `ai.onnx.ml` com conversão bidirecional para nós da IR (`to_nodes`/`from_node`), cobrindo os ~40 operadores de ML clássico e o subconjunto mínimo de ops `ai.onnx` (Cast, Reshape, Concat, Gather, Identity).
- `onnx-export`: Framework de exportação genérico (feature `export`): trait `ToOnnx`, `GraphBuilder`, `export_model`, e derive macro `OnnxExport` para o caso de mapeamento direto campo→atributo.
- `onnx-import`: Decode de arquivos `.onnx` para grafo semântico reconhecível (feature `import`): pattern matching de nós contra ops tipados, retenção fiel de nós desconhecidos como `Raw`.

### Modified Capabilities

(nenhuma — projeto novo, sem specs existentes)

## Impact

- **Código**: cria workspace com crates `serde-onnx` (módulos `ir`, `ml`, `proto`, `export` (gated), `import` (gated)) e `serde-onnx-macros`. Substitui o `Cargo.toml`/`src` atuais (hoje vazios).
- **Dependências novas**: `prost` + `prost-build` (codegen), `prost-types` (não, proto próprio), `half` (f16/bf16), `num-traits` (conversões checked); dev-dependencies: `proptest` (round-trip property tests).
- **Consumidor principal**: sciencekit implementará `ToOnnx` nos modelos fitted (ex.: `SKStandardScalerModel` → nó `Scaler` do `ai.onnx.ml`). O adaptador entre `SKFloat` (sciencekit) e `Scalar` (aqui) fica no lado do consumidor.
- **Fase 2 (fora do escopo)**: ops NN do `ai.onnx` completos, subgrafos (`If`/`Loop`/`Scan`), FunctionProto/training_info.
- **Riscos**: cobertura parcial de ops → nós desconhecidos devem ser retidos fielmente (raw), nunca descartados; versionamento de opsets → fixar opset alvo e rejeitar modelos fora dele com erro claro.
