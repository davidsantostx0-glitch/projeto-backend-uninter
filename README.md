# projeto-backend-uninter
Sistema de gerenciamento de pedidos desenvolvido com FastAPI para o Projeto Multidisciplinar.
# API Raízes do Nordeste

API Back-End desenvolvida com FastAPI para o projeto multidisciplinar do curso de Análise e Desenvolvimento de Sistemas.

O sistema tem como objetivo gerenciar o fluxo principal de pedidos da rede Raízes do Nordeste, contemplando autenticação de usuários, cadastro e consulta de produtos, criação de pedidos com identificação obrigatória do canal de origem, simulação de pagamento mock e atualização de status do pedido.

## Tecnologias utilizadas

* Python
* FastAPI
* Uvicorn
* SQLite
* SQLAlchemy
* Pydantic
* Swagger/OpenAPI
* Postman
* Git e GitHub

## Como executar o projeto

1. Clone o repositório:

```bash
git clone https://github.com/davidsantostx0-glitch/projeto-backend-uninter.git
```

2. Acesse a pasta do projeto:

```bash
cd projeto-backend-uninter
```

3. Crie e ative o ambiente virtual:

```bash
python -m venv venv
```

No Windows:

```bash
venv\Scripts\activate
```

4. Instale as dependências:

```bash
pip install -r requirements.txt
```

5. Execute a API:

```bash
uvicorn app.main:app --reload
```

6. Acesse a documentação Swagger/OpenAPI:

```text
http://127.0.0.1:8000/docs
```

## Principais endpoints

| Método | Rota                        | Descrição                                      |
| ------ | --------------------------- | ---------------------------------------------- |
| POST   | /auth/login                 | Realiza login e retorna token Bearer           |
| POST   | /usuarios                   | Cadastra usuário                               |
| GET    | /produtos                   | Lista produtos                                 |
| POST   | /produtos                   | Cadastra produto                               |
| POST   | /pedidos                    | Cria pedido                                    |
| GET    | /pedidos                    | Lista pedidos e permite filtro por canalPedido |
| GET    | /pedidos/{pedido_id}        | Consulta pedido específico                     |
| PUT    | /pedidos/{pedido_id}/status | Atualiza status do pedido                      |
| POST   | /pagamentos/mock            | Simula pagamento aprovado ou recusado          |
| GET    | /estoque/{produto_id}       | Consulta estoque do produto                    |

## Testes com Postman

A coleção Postman está disponível na pasta `postman` do repositório.

Para testar:

1. Abra o Postman.
2. Importe o arquivo JSON da coleção.
3. Execute primeiro o teste de login para gerar o token.
4. Use o token Bearer nas requisições protegidas.
5. Execute os testes positivos e negativos organizados nas pastas Auth, Produtos, Pedidos, Pagamentos e Erros.

## Fluxo principal do MVP

O fluxo priorizado no MVP foi:

```text
Pedido → Pagamento mock → Atualização de status
```

Esse fluxo valida:

* criação de pedido com canalPedido obrigatório;
* validação de produto e estoque;
* cálculo do valor total;
* simulação de pagamento aprovado ou recusado;
* atualização do status do pedido para PAGO ou PAGAMENTO_RECUSADO.

## Observações

Este projeto foi desenvolvido para fins acadêmicos, com execução local e banco SQLite para persistência dos dados de teste.
