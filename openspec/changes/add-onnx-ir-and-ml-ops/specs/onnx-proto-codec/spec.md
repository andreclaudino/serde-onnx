# onnx-proto-codec

## Purpose

Codec binário protobuf entre a IR em memória e arquivos `.onnx`, gerado a partir dos `.proto` oficiais do ONNX, cobrindo ModelProto, GraphProto, NodeProto, AttributeProto e TensorProto, incluindo raw_data little-endian e suporte a external data.

## ADDED Requirements

### Requirement: Encode de IR para arquivo .onnx
A biblioteca SHALL codificar um Model em memória para bytes no formato protobuf ONNX (e consequentemente para arquivo .onnx), preenchendo os campos ModelProto correspondentes: ModelProto, GraphProto, NodeProto, AttributeProto, TensorProto, TypeProto e TensorShapeProto.

#### Scenario: Modelo construído em memória vira arquivo
- **WHEN** um Model com um nó Scaler e um initializer é codificado
- **THEN** o resultado é um buffer protobuf válido decodificável pelo próprio codec

#### Scenario: Round-trip de modelo real
- **WHEN** um arquivo .onnx é decodificado para IR e re-encodificado
- **THEN** o segundo arquivo é semanticamente igual ao primeiro (valores, nomes, tipos, shapes, atributos preservados)

### Requirement: Decode de arquivo .onnx para IR
A biblioteca SHALL decodificar bytes/arquivo .onnx para a IR em memória, mapeando todos os campos do protobuf para o modelo em memória; bytes de dados de tensor crus SHALL ser convertidos para as variantes tipadas de acordo com o dtype declarado no TensorProto.

#### Scenario: Decode de arquivo válido
- **WHEN** um arquivo .onnx válido é decodificado
- **THEN** a IR resultante preserva nodes, initializers, inputs/outputs, value_info, atributos e metadados do modelo

#### Scenario: Decode de dtype conhecido
- **WHEN** um initializer com raw_data e elem_type DOUBLE é decodificado
- **THEN** o tensor em memória fica na variante F64 com os valores corretos

### Requirement: Erros claros em decode inválido
O decode SHALL retornar erro descritivo quando os bytes não formam um protobuf ONNX válido, quando um dados tipados/tamanho divergem (ex.: número de bytes não múltiplo do tamanho do elemento), ou quando o IR version ou opsets importados excedem os suportados pela biblioteca.

#### Scenario: Bytes corrompidos
- **WHEN** bytes arbitrários não suficientes para protobuf são decodificados
- **THEN** é retornado erro de formato sem pânico

#### Scenario: Tamanho divergente de dados de tensor
- **WHEN** um TensorProto declara 10 elementos f32 mas o raw_data tem 37 bytes
- **THEN** o decode retorna erro indicando o conflito

#### Scenario: IR version não suportada
- **WHEN** um modelo declara um opset/IR acima do suportado
- **THEN** o decode retorna erro identificando a versão e a suportada pela biblioteca

### Requirement: Suporte a external data
Tensores com dados externos (arquivo separado, offset, length, checksum) SHALL ser decodificados em um modo de referência: a IR deve preservar a localização dos dados (referência ao caminho relativo e offset), e SHALL prover leitura dos dados externos quando o caminho for resolvido; dados externos NÃO SHALL ser carregados implicitamente.

#### Scenario: Referência preservada em decode
- **WHEN** um initializer declara dados externos (arquivo, offset, tamanho)
- **THEN** a IR preserva essas informações sem carregar os bytes

#### Scenario: Leitura de dados externos resolvida
- **WHEN** a leitura de dados externos é solicitada com o diretório base do modelo
- **THEN** os bytes são lidos do arquivo externo na posição/offset anunciados e convertidos para a variante tipada
