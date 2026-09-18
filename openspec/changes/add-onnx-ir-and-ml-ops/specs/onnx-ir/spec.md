# onnx-ir

## Purpose

Modelo em memória do grafo ONNX conforme o IR spec: estruturas Model, Graph, Node, Attribute, Tensor e TypeProto que permitem inspecionar, construir e transformar modelos ONNX antes da serialização, com semântica SSA, namespaces de nomes e validação estrutural básica.

## ADDED Requirements

### Requirement: Hierarquia de modelo em memória
A IR SHALL representar um modelo ONNX como Model (ir_version, opset_import, producer info, metadata, functions listados como dados não processados nesta fase) contendo um Graph (nodes em ordem topológica, initializers nomeados, inputs/outputs/value_info tipados), onde cada Node possui name opcional, op_type, domain, inputs/outputs posicionais e atributos nomeados.

#### Scenario: Construção de um modelo mínimo
- **WHEN** um Model é construído com um Graph de um nó e um initializer
- **THEN** o grafo mantém a lista de nós e o initializer acessíveis pelo nome, e os inputs/outputs do grafo possuem ValueInfo com nome, tipo e shape

#### Scenario: Metadados de modelo
- **WHEN** um Model exporta producer_name, producer_version, domain e model_version
- **THEN** esses valores ficam preservados no round-trip encode/decode

### Requirement: SSA de outputs de nós
A IR SHALL garantir que nomes de outputs de nós sejam únicos dentro de um grafo (single static assignment); a construção programática de um nó cujo output colide com output de outro nó do mesmo grafo SHALL retornar erro.

#### Scenario: Output duplicado rejeitado no builder
- **WHEN** dois nós no mesmo grafo declaram o mesmo nome de output
- **THEN** a construção/validação do grafo retorna erro indicando o nome duplicado

#### Scenario: Modelo externo com nomes únicos decodificado
- **WHEN** um arquivo .onnx válido (outputs únicos) é decodificado
- **THEN** todos os outputs dos nós ficam acessíveis sem colisão

### Requirement: Referências de valores via nomes
Edges do grafo SHALL ser estabelecidas por nomes: um input de nó pode referenciar um graph input, um initializer ou o output de outro nó do mesmo grafo; a IR SHALL permitir verificar a definição de cada valor usado.

#### Scenario: Input referencia output anterior
- **WHEN** o nó B recebe como input o nome de um output do nó A
- **THEN** a IR resolve a referência B→A na checagem de definição de valores

#### Scenario: Referência a valor indefinido detectada
- **WHEN** um input de nó referencia um nome que não é graph input, initializer nem output de nó anterior
- **THEN** a validação do grafo retorna erro de valor indefinido

### Requirement: Atributos com oneof de valores
Um Attribute SHALL ter nome e exatamente um valor dentre os tipos ONNX: Float(f32), Int(i64), String(String), Tensor, Graph (reservado como variante, decode completo na fase 2), e listas Floats/Ints/Strings/Tensors/Graphs; mais de um campo de valor preenchido SHALL ser erro de construção.

#### Scenario: Atributo com um único valor
- **WHEN** um atributo "axis" do tipo Int é construído
- **THEN** ele carrega apenas o valor inteiro e o nome

#### Scenario: Atributo com valores conflitantes
- **WHEN** um atributo é construído com Int e Floats simultaneamente
- **THEN** a construção retorna erro

### Requirement: TypeProto com tipos recursivos
ValueType SHALL representar os tipos de entrada/saída ONNX: Tensor, SparseTensor, Sequence, Map e Optional, com elemento tipado (ElemType ONNX completo: floats, ints signed/unsigned 2–64 bits, bool, string, complex) e shape composta de dimensões Fixed(i64)/Param(String)/Unknown.

#### Scenario: Tipo tensor com shape parcialmente conhecida
- **WHEN** um ValueType Tensor FLOAT é construído com shape [Fixa(N), Param("M")]
- **THEN** o tipo preserva elem type, dimensão fixa e dimensão simbólica

#### Scenario: Tipo sequência de tensores
- **WHEN** um ValueType Sequence contendo Tensor é construído
- **THEN** o tipo aninhado fica acessível via decomposição da variante

### Requirement: Validação estrutural do grafo
A IR SHALL expor validação estrutural que verifica: presença de nome no grafo, definição de inputs/outputs do grafo principal com shape (rank), topologia ordenada dos nós, e retorno de erros descritivos listando as violações.

#### Scenario: Grafo válido passa na validação
- **WHEN** um grafo bem formado é validado
- **THEN** a validação retorna Ok

#### Scenario: Ciclo detectado via referências
- **WHEN** um grafo contém referência circular entre valores
- **THEN** a validação retorna erro de ciclo no grafo

### Requirement: Variadic e optional inputs/outputs
A IR SHALL permitir nós com número variável de inputs/outputs (variadic com aridade mínima definida pelo op) e inputs/outputs opcionais ausentes (omitidos no fim ou representados por string vazia "");

#### Scenario: Nó com inputs opcionais omitidos
- **WHEN** um nó é construído sem preencher um input opcional final
- **THEN** o nó é válido com essa posição ausente

#### Scenario: Input opcional vazio por string vazia
- **WHEN** um nó define um input com nome ""
- **THEN** a IR trata a posição como opcional não preenchida
