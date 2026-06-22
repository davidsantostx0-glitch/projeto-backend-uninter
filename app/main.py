from fastapi import FastAPI

app = FastAPI(
    title="API Raízes do Nordeste",
    version="1.0.0",
    description="Sistema de gerenciamento de pedidos desenvolvido com FastAPI para o Projeto Multidisciplinar."
)

@app.get("/")
def home():
    return {
        "mensagem": "API Raízes do Nordeste funcionando com sucesso!"
    }