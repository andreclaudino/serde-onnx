# Tasks: ONNX IR, ai.onnx.ml ops e framework de exportação (Fase 1)

## 1. Workspace e infraestrutura

- [x] 1.1 Converter para workspace de duas crates: `serde-onnx` (lib) e `serde-onnx-macros` (proc-macro crate, `proc-macro = true`), ajustando raiz `Cargo.toml` (workspace members, edition 2024)
- [x] 1.2 Definir features: `export` (opcional, pull de `serde-onnx-macros`), `import` (opcional); dev-dependencies: `proptest`; deps: `prost`, `num-traits`, `half`
- [x] 1.3 Vendor dos `.proto` oficiais do onnx (onnx.proto3, onnx-operators.proto3, onnx-ml.proto3, onnx-operators-ml.proto3) em `third_party/` com changelog de origem (commit do upstream) e script `xtask`-like ou build.rs configurando prost-build
- [x] 1.4 Gerar módulo `proto` com prost-build (imports, pacote onnx; compilando cargo build limpo sem warnings)

## 2. IR base (module `ir`)

- [x] 2.1 Definir `ElemType` (enum completo ONNX) e `ValueType` (Tensor/SparseTensor/Sequence/Map/Optional) com `Dim` (Fixed/Param/Unknown) e shape; derives Debug/Clone/PartialEq
- [x] 2.2 Definir `Tensor { dtype, shape, data: TensorData }` e `TensorData` enum tipado (F32,F64,I8..I64,U8..U64,Bool,String,F16,Bf16,RawBytes) — specs onnx-numeric-types/as de base do enum
- [x] 2.3 Definir `Attribute { name, value: AttributeValue }` com oneof (Float/Int/String/Tensor/Graph(reservado)/Floats/Ints/Strings/Tensors/Graphs) e erro em construção com mais de um valor
- [x] 2.4 Definir `Node` (op_type, domain, name opcional, inputs/outputs, attributes), `Graph` (nodes, initializers, input/output/value_info, name) e `Model` (ir_version, opset_import, producer, metadata, graph)
- [x] 2.5 Implementar validação estrutural: SSA (outputs únicos), definição de valores (inputs referenciam/graph initializer/output anterior), topologia ordenada (ciclos), grafo com nome, I/O do grafo principal com shape; com erros descritivos agregados
- [x] 2.6 Testes unitários da IR: construção mínima, SSA duplicado, valor indefinido, ciclo, atributos conflitantes, variadic/optional ("")

## 3. Numéricos seguros (module `numeric`/integrado à IR)

- [x] 3.1 Trait `Scalar` sealed (f32, f64, i8-i64, u8-u64, bool) com `ELEM_TYPE` associado e encode de bytes LE
- [x] 3.2 `Tensor::as_slice::<T>` (exato, erro TypeError em divergência) e `to_vec::<T>` (checked via NumCast, erro CastError com detalhe da perda)
- [x] 3.3 f16/bf16 via `half` leitura/escrita f32↔bits explícitas; fp8/int4/ficam RAW como bytes crus
- [x] 3.4 Testes property (proptest) de round-trip LE por tipo de elemento e de precisão em conversões checked

## 4. Codec protobuf (module `proto`)

- [x] 4.1 Mapeamento IR → protos gerados (encode): Model/Graph/Node/Attribute/Tensor/TypeProto, incluindo raw_data LE e campos de tensor data com caso correto por dtype (FLOAT→float_data como float32 LittleEndian, INT64→int64_data, STRING→string_data, RAW_DATA, EXTERNAL)
- [x] 4.2 Mapeamento protos → IR (decode): com validação de consistência dtype×tamanho (erro em tamanho divergente) e conversão de raw bytes para variante tipada
- [x] 4.3 External data: preservar referência (path relativo, offset, length, checksum) sem carregar bytes; API de leitura com diretório base
- [x] 4.4 Erros de decode: protobuf inválido, IR/opset acima do suportado (const de IR version/opset alvo), tamanho divergente de tensor
- [x] 4.5 Testes de round-trip encode/decode (idempotência semântica: nomes, valores, tipos, shapes, atributos preservados) incluindo modelo com external data (fixture .onnx pequeno criado no teste)

## 5. Ops tipados ai.onnx.ml + subconjunto ai.onnx (module `ml`)

- [x] 5.1 Trait local `OnnxOp` (associated OP_TYPE/DOMAIN) e implementações base `to_nodes(&GraphBuilder)`/`from_node(&Node)`
- [x] 5.2 Ops de pré-processamento node-únicos: Scaler, Imputer, Normalizer, LabelEncoder, OneHotEncoder, DictVectorizer, FeatureVectorizer (com to_nodes/from_node e testes)
- [x] 5.3 Ops lineares/SVM: LinearClassifier, LinearRegressor, SVMClassifier, SVMRegressor (com initializers/atributos corretos por spec e testes)
- [x] 5.4 Ops de árvore: TreeEnsembleClassifier, TreeEnsembleRegressor (mapeamento completo de arrays de nós/limiares/split modes/leaf weights/post_transform/ZipMap-like ouputs conforme spec) e testes de round-trip total
- [x] 5.5 Ops de pós processamento: ZipMap; e subconjunto ai.onnx: Cast, Reshape, Concat, Gather, Identity (to_nodes/from_node e testes)
- [x] 5.6 Factory de reconhecimento: `make_node_payload(node) -> NodePayload` com match (domain, op_type) sobre os ops suportados, fallback Raw (sem perda), incl. elemento de NodePayload enum e casos de teste de reconhecimento e Raw

## 6. Export framework (feature `export`, module `export`)

- [x] 6.1 `GraphBuilder`: inputs tipados (nome + ValueType), initializers genéricos via Scalar (dtype automático), nós com outputs auto-nomeados (colisão = erro), registro de opsets importados
- [x] 6.2 trait `ToOnnx` (to_graph(&mut GraphBuilder) -> ValueRef) + `export_model` produz Model validado (validação estrutural antes de serializar; erro agregado)
- [x] 6.3 crate `serde-onnx-macros`: derive `OnnxExport` com atributos `#[onnx(op, domain, attr, ty)]` (campo → atributo único nó) e erros claros de anotações inválidas; re-export via `serde_onnx::export`
- [x] 6.4 Teste de integração com derive: struct Scaler-like derivada produz mesmo grafo que impl manual equivalente
- [x] 6.5 Exemplo/scenario documentado de integração consumer (simula SKStandardScalerModel): struct com campos mean/std exportando WeScaler node `Scaler` do ai.onnx.ml

## 7. Import com reconhecimento (feature `import`)

- [x] 7.1 API decode de arquivo .onnx → grafo semântico: classificação por (domain, op_type) via NodePayload, assinatura acessível (inputs/outputs/initializers)
- [x] 7.2 Marcação não-fatal de recursos fora do escopo (subgrafos If/Loop/Scan preservados como dados, avisável; Visitor distingue tipado/Raw)
- [x] 7.3 Round-trip export → encode → decode → reconhecimento: modelo com Scaler recuperado tipado igual; ensembles TreeEnsembleClassifier idem (feature export+import juntas dev)

## 8. Qualidade final da fase

- [x] 8.1 `cargo clippy` sem warnings e `cargo fmt` aplicado
- [x] 8.2 Doc de repositório para fase 2: README com mapa de módulos, opsets alvo e lista de não implementado (subgrafos/FunctionProto/training_info/ai.onnx completo)
