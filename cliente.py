from Pyro5.server import Daemon
from Pyro5.core import locate_ns
from Pyro5.api import Proxy
from Pyro5.server import expose, callback

from threading import Thread

@expose
@callback
class ClienteCallback:
    def __init__(self, usuario):
        self.usuario = usuario

    def set_uri(self, uri):
        self.uri = uri
    def notificacao(self, mensagem):
        print(mensagem)
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
        print("Usuário cadastrado com sucesso")

        daemon = Daemon()
        cliente_callback = ClienteCallback(usuario)
        uri_cliente_callback = daemon.register(cliente_callback)
        cliente_callback.set_uri(uri_cliente_callback)

        thread = Thread(target=cliente_callback.loopThread, args=(daemon,))
        thread.daemon = True
        thread.start()

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

        leilao.add_produto(codigo, nome, descricao, preco_inicial, duracao, cliente_callback.uri)
        print("Produto cadastrado com sucesso")
    
    elif op == 4 and not cliente_callback:
        print("É necessário cadastrar um usuário antes de dar um lance")
    elif op == 4:
        print("*** DAR LANCE ***")
        codigo = int(input("Código: "))
        valor = float(input("Valor: "))
        
        lance_mensagem = leilao.dar_lance(codigo, valor, comprador=cliente_callback.usuario, uri=cliente_callback.uri)

        print(lance_mensagem)

    elif op == 5:
        print(leilao.test())
    

if __name__ == '__main__':
    main()
