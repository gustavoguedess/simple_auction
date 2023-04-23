from Pyro5.server import expose, Daemon, oneway
from Pyro5.core import locate_ns
from Pyro5.api import Proxy

from threading import Thread
from datetime import datetime, timedelta
import time

class Produto:
    def __init__(self, codigo, nome, descricao, preco_inicial, duracao, uri):
        self.codigo = codigo
        self.nome = nome
        self.descricao = descricao
        self.tempo_final = datetime.now() + timedelta(seconds=duracao) 
        self.lance = preco_inicial
        self.comprador = ""
        self.uri_interessados = [uri]

    def set_lance(self, valor, comprador, uri):
        if valor > self.lance or (valor >= self.lance and self.comprador==""):
            self.lance = valor
            self.comprador = comprador
            if uri not in self.uri_interessados:
                self.uri_interessados.append(uri)
            for uri in self.uri_interessados:
                cliente = Proxy(uri)
                cliente.notificacao(f"Novo lance no produto {self.nome} de R$ {self.lance}")

            return True
        return False

    def disponivel(self):
        return self.tempo_final > datetime.now()
    
class Leilao:
    def __init__(self):
        self.produtos = []
    
    @expose
    @oneway
    def add_produto(self, codigo, nome, descricao, preco_inicial, duracao, uri):
        produto = Produto(codigo, nome, descricao, preco_inicial, duracao, uri)
        self.produtos.append(produto)

    @expose
    def get_produtos(self):
        lista_produtos = []
        for produto in self.produtos:
            lista_produtos.append(produto.__dict__)
        
        return lista_produtos

    @expose
    def dar_lance(self, codigo, valor, comprador, uri):
        for produto in self.produtos:
            if produto.codigo == codigo:
                if produto.set_lance(valor, comprador, uri):
                    return "Lance efetuado com sucesso! :)"
                return "Lance não aceito. Valor menor que o atual"
        return "Produto não encontrado"
    
    def disponivel(self, codigo):
        for produto in self.produtos:
            if produto.codigo == codigo:
                return produto.disponivel()
        return False

    def remove_produto(self, codigo):
        for produto in self.produtos:
            if produto.codigo == codigo:
                self.produtos.remove(produto)
                return True
        return False

leilao = Leilao()

def main():
    print("Servidor de leilão iniciado")

    while True:
        lista_produtos = leilao.get_produtos()
        for produto in lista_produtos:
            if not leilao.disponivel(produto['codigo']):
                for uri in produto['uri_interessados']:
                    cliente = Proxy(uri)
                    cliente.notificacao(f"Produto {produto['nome']} expirou. O comprador foi {produto['comprador']} com o valor de R$ {produto['lance']}")
                print(f"Produto {produto['codigo']} expirou")
                leilao.remove_produto(produto['codigo'])
        time.sleep(5)

if __name__ == '__main__':
    servidor_nomes = locate_ns()

    daemon = Daemon()

    uri = daemon.register(leilao)
    servidor_nomes.register("leilao", uri)

    thread = Thread(target=main)
    thread.start()

    daemon.requestLoop()

    servidor_nomes.remove("leilao")
    print("Servidor de leilão removido do servidor de nomes")

    daemon.close()
        