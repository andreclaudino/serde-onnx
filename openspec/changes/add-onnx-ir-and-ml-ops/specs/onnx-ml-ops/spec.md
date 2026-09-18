# onnx-ml-ops

## Purpose

Ops tipados do domínio `ai.onnx.ml` (e o subconjunto mínimo de ops do domínio `ai.onnx` usados por pipelines clássicos) representados como structs Rust com hiperparâmetros tipados, cada op com conversão bidirecional para nós da IR (`to_nodes`/`from_node`), permitindo export e reconhecimento semântico em decode.

## ADDED Requirements

### Requirement: Ops ai.onnx.ml como structs tipadas
Cada operador do domínio `ai.onnx.ml` suportado nesta fase SHALL ser representado por uma struct Rust com os hiperparâmetros como campos tipados (ex.: Scaler com offset: Vec<f32> e scale: Vec<f32>); a lista cobre os ~40 operadores do domínio, incluindo Scaler, Imputer, Normalizer, LinearClassifier, LinearRegressor, TreeEnsembleClassifier, TreeEnsembleRegressor, SVMClassifier, SVMRegressor, LabelEncoder, OneHotEncoder, DictVectorizer, FeatureVectorizer, ZipMap.

#### Scenario: Op de Árvore representado tipadamente
- **WHEN** um TreeEnsembleClassifier é representado
- **THEN** os arrays de nós, limiares, modos de split e pesos de folhas ficam como campos tipados acessíveis

#### Scenario: Op simples único nó
- **WHEN** um Scaler é representado com offset e scale
- **THEN** os dois atributos ficam como campos tipados da struct

### Requirement: Conversão op → nós da IR (to_nodes)
Cada op tipado SHALL fornecer to_nodes que produz os nós da IR, os initializers necessários (ex.: coeficientes de LinearClassifier) e a assinatura de entrada/saída, prefixando nomes de valores de forma determinística; a conversão NÃO SHALL alterar dados (lossless), e ops que requerem atributos não preenchidos SHALL retornar erro descritivo.

#### Scenario: LinearClassifier exportado
- **WHEN** to_nodes é chamado em um LinearClassifier com coeficientes e interceptos
- **THEN** um nó `LinearClassifier` é produzido com os atributos completos (coefficients como atributo ou tensor conforme o operador no spec), e um initializer (quando o op definem tensor) e ValueInfo de entrada e saída coerente (output class_ids/labels conforme spec)

#### Scenario: Op com campo obrigatório ausente
- **WHEN** to_nodes é chamado em um op sem campo obrigatório
- **THEN** é retornado erro indicando o campo e o operador

### Requirement: Conversão nó da IR → op tipado (from_node)
Cada op tipado (especificamente sua assinatura, atributos e inputs/outputs) SHALL fornecer from_node que reconstrói o struct Rust a partir de um nó da IR quando o domain/op_type/campos correspondem; nodes de outro domain ou com campos inválidos/ausentes SHALL resultar em erro de reconhecimento descritivo.

#### Scenario: nó Scaler reconhecido
- **WHEN** from_node é chamado com um nó da IR com op_type "Scaler", domain "ai.onnx.ml"
- **THEN** a struct Scaler é reconstruída com os atributos lidos

#### Scenario: nó de domain desconhecido
- **WHEN** from_node é chamado para um nó com domain externo não registrado
- **THEN** é retornado erro não recognizing (deve ser tratado como Raw) sem crash

### Requirement: Subconjunto mínimo de ops ai.onnx
Os operators essenciais para compor pipelines clássicos SHALL estar suportados como ops tipados do domínio `ai.onnx`: Cast, Reshape, Concat, Gather e Identity; outros op_type do iniciar um Nó sem payload tipado SHALL permanecer como nó genérico (Raw), sem erro.

#### Scenario: Pipeline com Cast e Reshape
- **WHEN** um grafo contém nós Cast e Reshape tipados seguidos de Scaler
- **THEN** os três nós ficam disponíveis como ops tipados nos seus respectivos domínios

### Requirement: Round-trip sem perda por op
Para cada op suportado, a conversão op → IR → op SHALL preservar todos os hiperparâmetros, incluindo valores default (reaplicados como constantes) e campos opcionais ausentes; um round-trip resultante SHALL produzir struct igual à original para qualquer hiperparâmetro configurado.

#### Scenario: Round-trip TreeEnsembleClassifier
- **WHEN** um TreeEnsembleClassifier com todos os campos definidos é convertido para IR e de volta
- **THEN** a struct resultante é igual à original (todos os arrays e atributos iguais)

#### Scenario: Round-trip mantendo defaults ausentes
- **WHEN** um Scaler sem envolver defaults de post_transform é exportado e decodificado
- **THEN** os defaults ausentes continuam ausentes (não materializados artificially) quando o op da especificação o tratar como default de leitura
