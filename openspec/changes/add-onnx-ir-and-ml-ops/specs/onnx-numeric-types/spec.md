# onnx-numeric-types

## Purpose

Representação segura dos tipos numéricos ONNX em tensores e atributos: armazenamento tipado sem punning, mapeamento sealed entre tipos Rust e ElemType ONNX, e conversões sempre explícitas e checked, sem perda silenciosa de dados.

## ADDED Requirements

### Requirement: Armazenamento tipado de dados de tensor
Os dados de um Tensor SHALL ser armazenados em enum com variantes tipadas por elemento (F32, F64, I8, I16, I32, I64, U8, U16, U32, U64, Bool, String, F16, Bf16 e cru em bytes para tipos exóticos), com o dtype derivado da variante; dados crus (raw bytes) SHALL existir apenas na camada de serialização.

#### Scenario: Tensor f32 mantém slices tipados
- **WHEN** um tensor é criado com dados de f32
- **THEN** o dtype resultante é FLOAT e o acesso como slice de f32 retorna os dados sem cópia

#### Scenario: Tipos de meia precisão armazenados como bits
- **WHEN** um tensor F16 é criado
- **THEN** os dados ficam armazenados como bits (u16) na variante dedicada, e a leitura como f32 é uma operação explícita de conversão

### Requirement: Trait Scalar sealed com mapeamento para ElemType
A biblioteca SHALL expor uma trait Scalar sealed, implementada apenas pelos tipos Rust correspondentes a ElemTypes ONNX (f32, f64, i8–i64, u8–u64, bool), cada um com o ElemType ONNX associado; tipos fora do conjunto (ex.: u128, usize) não SHALL poder implementá-la.

#### Scenario: inicializador tipado Static
- **WHEN** um initializer é criado a partir de um slice de f64
- **THEN** o tensor resultante tem dtype DOUBLE automaticamente

#### Scenario: Tipo não ONNX rejeitado
- **WHEN** um código tenta criar um initializer a partir de um slice de um tipo sem Scalar
- **THEN** a compilação falha (trait não implementada)

### Requirement: Acesso exato a dados tipados
Tensor SHALL expor acesso a dados as_slice::<T>, que retorna o slice interno quando o tipo T casa exatamente com a variante armazenada, e erro TypeError quando não casa; nenhuma conversão numérica implícita SHALL ocorrer nesse acesso.

#### Scenario: Acesso exato bem-sucedido
- **WHEN** um tensor F64 é acessado com as_slice::<f64>
- **THEN** o slice de f64 é retornado com Ok

#### Scenario: Acesso com dtype divergente falha
- **WHEN** um tensor F32 é acessado com as_slice::<f64>
- **THEN** é retornado erro indicando divergência de tipo (FLOAT vs DOUBLE)

### Requirement: Conversões numéricas sempre explícitaas e checked
Toda conversão de elementos entre tipos numéricos SHALL ser explícita (to_vec::<T>) e checked: valores que não representam fielmente (ex.: f64 fracionário para i64, u64 acima do range representável de f32) geram erro; nunca SHALL haver casts com perda silenciosa (sem `as` não verificado) no código da biblioteca aplicado a dados de usuário.

#### Scenario: Conversão sem perda sucedida
- **WHEN** um tensor I32 com valores pequenos é convertido com to_vec::<i64>
- **THEN** os valores são convertidos e Ok é retornado

#### Scenario: Conversão com perda rejeitada
- **WHEN** um tensor F32 é convertido com to_vec::<i64>
- **THEN** é retornado erro descrevendo que a conversão perderia informação

### Requirement: Atributos restritos a f32 e i64
Atributos numéricos (Float/Int e listas Floats/Ints) SHALL aceitar somente f32 e i64 conforme o spec ONNX; encode de um valor que não representa (ex.: u64 acima de i64::MAX em atributo Int) SHALL retornar erro em vez de truncar.

#### Scenario: Atributo Int com valor dentro do range
- **WHEN** um atributo Int é construído com um i64
- **THEN** ele persiste no round-trip encode/decode

#### Scenario: Valor fora do range em atributo
- **WHEN** um valor u64 acima de i64::MAX é passado para um atributo Int
- **THEN** é retornado erro de range, sem truncamento silencioso

### Requirement: Serialização little-endian explícita
Na fronteira de serialização, os dados de tensor SHALL ser codificados como little-endian explícitao (to_le_bytes/from_le_bytes por elemento), garantindo portabilidade entre arquiteturas; o decode aplica o mapeamento inverso com base no dtype declarado.

#### Scenario: Round-trip byte exato
- **WHEN** um tensor F32 é codificado e decodificado
- **THEN** os bytes do raw_data são little-endian e o valor dos elementos é idêntico ao original
