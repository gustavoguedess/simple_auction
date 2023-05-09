from Pyro5.server import Daemon
from Pyro5.core import locate_ns
from Pyro5.api import Proxy, config
from Pyro5.server import expose, callback

from threading import Thread

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
import base64

@callback
class ClienteCallback:
    def __init__(self, usuario):
        self.usuario = usuario
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        self.public_key = self.private_key.public_key()
        self.uri = None

    @expose
    def notificacao(self, mensagem):
        print(mensagem)

    def set_uri(self, uri):
        self.uri = uri

    def loopThread(self, daemon):
        daemon.requestLoop()


def main():
    global leilao
    global cliente_callback 

    cliente_callback = None
    servidor_nomes = locate_ns()
    uri = servidor_nomes.lookup("leilao")
    leilao = Proxy(uri)  


    print("\033c", end="")
    while True:
        menu()
        

def menu():
    print("--------------------------")
    print("Menu")
    print("1. Cadastrar usuário")
    print("2. Consultar leilões ativos")
    print("3. Cadastrar produto")
    print("4. Dar lance em um produto")

    op = int(input("Opção: "))
    print("\033c", end="")

    if op == 1:
        global cliente_callback
        print("*** CADASTRO DE USUÁRIO ***")
        usuario = input("Usuário: ")

        daemon = Daemon()
        config.SERIALIZER = "marshal"
        cliente_callback = ClienteCallback(usuario)
        uri_cliente_callback = daemon.register(cliente_callback)
        cliente_callback.set_uri(uri_cliente_callback)

        pem_public_key = cliente_callback.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo)

        leilao.cadastrar_usuario(usuario, uri_cliente_callback, pem_public_key)

        thread = Thread(target=cliente_callback.loopThread, args=(daemon,))
        thread.daemon = True
        thread.start()
        print("Usuário cadastrado com sucesso")

    elif op == 2:
        print("*** LEILÕES ATIVOS ***")
        lista_produtos = leilao.get_produtos()

        print("cod | nome | descricao | valor | comprador | tempo final")
        for produto in lista_produtos:
            print(f"{produto['codigo']} | {produto['nome']} | {produto['descricao']} | {produto['lance']} | {produto['comprador']} | {produto['tempo_final']}")

    elif op == 3 and not cliente_callback:
        print("É necessário cadastrar um usuário antes de cadastrar um produto")
    elif op == 3:
        print("*** CADASTRO DE PRODUTO ***")
        codigo = int(input("Código: "))
        nome = input("Nome: ")
        descricao = input("Descrição: ")
        preco_inicial = float(input("Preço inicial: "))
        duracao = int(input("Duração (segundos): "))

        leilao.add_produto(codigo, nome, descricao, preco_inicial, duracao, cliente_callback.usuario)
        print("Produto cadastrado com sucesso")
    
    elif op == 4 and not cliente_callback:
        print("É necessário cadastrar um usuário antes de dar um lance")
    elif op == 4:
        print("*** DAR LANCE ***")
        codigo = int(input("Código: "))
        valor = float(input("Valor: "))
        
        signature = cliente_callback.private_key.sign(
            str(str(codigo) + str(valor)).encode("utf-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        lance_mensagem = leilao.dar_lance(cliente_callback.usuario, codigo, valor, signature)

        print(lance_mensagem)
    

if __name__ == '__main__':
    main()
