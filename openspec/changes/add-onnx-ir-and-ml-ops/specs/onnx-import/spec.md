# onnx-import

## Purpose

Decode de arquivos `.onnx` para grafo semântico reconhecível (feature `import`): nós cujo op é conhecido nos domínios suportados viram payload tipado; desconhecidos são retidos fielmente como Raw, permitindo conversão a outros formatos por visitor.

## ADDED Requirements

### Requirement: Decode de arquivo .onnx para grafo reconhecível
A biblioteca (feature import) SHALL oferecer decodificação de arquivo .onnx para o grafo semântico: cada nó da IR é classificado por (domain, op_type) e, quando reconhecido entre os ops tipados suportados (ai.onnx.ml e o subconjunto de ai.onnx), recebe payload tipado; a assinatura do modelo fica acessível (inputs/outputs/initializers).

#### Scenario: Modelo com Scaler decodificado com reconhecimento
- **WHEN** um arquivo .onnx contendo um nó Scaler é decodificado
- **THEN** o nó resultante tem payload tipado Scaler com atributos materializados

#### Scenario: Assinatura do modelo acessível
- **WHEN** qualquer arquivo .onnx é decodificado
- **THEN** inputs (com ValueType/shape), outputs e initializers ficam acessíveis no grafo

### Requirement: Nós desconhecidos retidos fielmente
Nós cujo (domain, op_type) não tem op tipado suportado SHALL permanecer na IR como payload Raw, preservando todos os atributos, inputs/outputs e metadados originais sem alteração; a decodificação NÃO SHALL falhar por causa de nós desconhecidos.

#### Scenario: Modelo com ops não suportados decodifica
- **WHEN** um arquivo .onnx contém ops fora da cobertura suportada
- **THEN** o decode é bem-sucedido e esses nós ficam em Raw, com todos os dados preservados

#### Scenario: Visitor pode tratar Raw e tipado
- **WHEN** um consumidor percorre o grafo decodificado
- **THEN** cada nó é discernível entre payload tipado e Raw

### Requirement: Rejeição explícita fora do opset alvo
Modelos que usam recursos fora do escopo desta fase (subgrafos If/Loop/Scan como atributos, FunctionProto usados como referência de execução SEM corpo resolvível) são decodificados mas SHALL ser marcados: subgrafos em atributos do domínio ai.onnx são preservados como dados não processados e sinalizados no resultado (aviso no decode), sem bloquear o decode.

#### Scenario: Modelo com Loop decodificado com aviso
- **WHEN** um modelo contém atributos contendo subgrafos (If/Loop/Scan)
- **THEN** o decode retorna sucesso com marcação/erro não fatal sinalizando a área não totalmente suportada

#### Scenario: Modelo dentro do escopo decodifica limpo
- **WHEN** um modelo apenas com ops ai.onnx.ml e ai.onnx do subconjunto é decodificado
- **THEN** o decode não emite marcas de limitação

### Requirement: Feature import opcional
O módulo de import (decode para grafo reconhecível, pattern matching para ops tipados) SHALL estar disponível apenas com a feature import; sem ela, o codec básico (decode para IR genérico) permanece disponível.

#### Scenario: Compilação sem feature import
- **WHEN** a crate compila sem a feature import
- **THEN** decode de arquivo para IR genérica funciona, mas o pattern matching para ops tipados não está presente

#### Scenario: Round-trip com export e import habilitados
- **WHEN** um modelo clássico é exportado via feature export e decodificado com feature import
- **THEN** o grafo resultante reconhece os ops tipados e os hiperparâmetros são recuperados
