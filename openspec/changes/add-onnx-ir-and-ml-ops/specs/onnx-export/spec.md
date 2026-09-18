# onnx-export

## Purpose

Framework de exportação genérico (feature `export`): trait `ToOnnx`, builder de grafo que acumula nós/initializers/assinaturas, função de topo `export_model` e derive macro `OnnxExport` para o caso de mapeamento direto campo→atributo, permitindo que qualquer usuário exporte modelos fitted para ONNX com esforço mínimo.

## ADDED Requirements

### Requirement: Trait ToOnnx para estruturas exportáveis
A biblioteca SHALL expor uma trait ToOnnx cujo contrato é converter uma estrutura em um subgrafo dentro de um GraphBuilder, retornando a referência do valor de saída; qualquer modelo fitted (ex.: do sciencekit) implementando essa trait fica exportável.

#### Scenario: Modelo implementando ToOnnx
- **WHEN** uma struct de modelo implementa ToOnnx construindo um nó único
- **THEN** export_model produz um Model válido com base no builder criado

### Requirement: GraphBuilder acumula estrutura do grafo
O GraphBuilder SHALL permitir declarar inputs tipados (nome + ValueType), initializers a partir de slices tipados (dado genérico Scalar), e nós (op_type, domain, inputs, atributos), produzindo outputs de nós automaticamente nomeados (colisões rejeitadas) e acumulando os opsets importados declarados.

#### Scenario: Grafo com input, initializer e nó
- **WHEN** um builder declara um tensor de entrada, um initializer e um nó que consome ambos
- **THEN** o grafo resultante contém todos os elementos com nomes consistentes e sem colisão

#### Scenario: Declaração de opset no export
- **WHEN** um exportador declara uso de um op do domínio `ai.onnx.ml`
- **THEN** o Model final lista o opset import (domain ai.onnx.ml e versão alvo da biblioteca)

### Requirement: export_model produz Model validado
A função de topo export_model SHALL produzir um Model completo (opsets, grafo nomeado, outputs com ValueInfo) e SHALL executar validação estrutural da IR antes de devolver; exportação de grafo inválido SHALL retornar erro listando as violações.

#### Scenario: Modelo válido exportado
- **WHEN** export_model recebe uma estrutura implementando ToOnnx válida
- **THEN** o Model final passa na validação e contém opset_import correto

#### Scenario: Modelo inválido bloqueado na saída
- **WHEN** o builder acumula um grafo com referência a valor indefinido
- **THEN** export_model retorna erro descritivo da violação

### Requirement: Derive macro OnnxExport para mapeamento direto
A derive macro OnnxExport SHALL gerar impl ToOnnx para structs cujo comportamento é mapear campos para atributos de um único nó, configurada por atributos #[onnx(op = "...", domain = "...", attr = "opcional-field-name", ty = ...)] para indicar nome do op, domain e mapeamento campo→atributo; casos que exigem lógica (múltiplos nós, initializers derivados) permanecem na impl manual da trait.

#### Scenario: Derive de Scaler análogo
- **WHEN** uma struct com offset: Vec<f32> e scale: Vec<f32> deriva OnnxExport com op = Scaler, domain = ai.onnx.ml
- **THEN** export_model da struct produz o mesmo grafo de uma impl manual equivalente

#### Scenario: Campo sem anotação de attr não vira atributo
- **WHEN** um campo da struct não possui #[onnx(attr = ...)]
- **THEN** ele não é incluído como atributo (o comportamento deve ser escolhido explicitamente)

### Requirement: Feature export opcional
O framework de exportação (ToOnnx, GraphBuilder, export_model, macro reexportada) SHALL estar disponível apenas com a feature export habilitada (a proc-macro vive na crate serde-onnx-macros como dependência opcional); com a feature desativada compila somente a IR/codec/ops.

#### Scenario: Compilação sem feature export
- **WHEN** a crate compila com somente features default
- **THEN** os módulos de export e a macro não estão presentes

#### Scenario: Compilação com feature export
- **WHEN** a crate compila com feature export
- **THEN** ToOnnx, GraphBuilder, export_model e derive OnnxExport estão disponíveis
