from Pyro5.server import expose, Daemon, oneway
from Pyro5.core import locate_ns
from Pyro5.api import Proxy

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

import base64

from threading import Thread
from datetime import datetime, timedelta
import time

class Produto:
    def __init__(self, codigo, nome, descricao, preco_inicial, duracao, cliente):
        self.codigo = codigo
        self.nome = nome
        self.descricao = descricao
        self.tempo_final = datetime.now() + timedelta(seconds=duracao) 
        self.lance = preco_inicial
        self.comprador = ""
        self.clientes_interessados = [cliente]

    def set_lance(self, valor, cliente):
        if valor > self.lance or (valor >= self.lance and self.comprador==""):
            self.lance = valor
            self.comprador = cliente.usuario

            if cliente not in self.clientes_interessados:
                self.clientes_interessados.append(cliente)

            for cliente in self.clientes_interessados:
                cliente.proxy.notificacao(f"Novo lance no produto {self.nome} de R$ {self.lance}")

            return True
        return False

    def disponivel(self):
        return self.tempo_final > datetime.now()

class Cliente:
    def __init__(self, usuario, uri, chave_publica):
        self.usuario = usuario
        self.proxy = Proxy(uri)
        self.chave_publica = chave_publica

class Leilao:
    def __init__(self):
        self.produtos = []
        self.chaves_publicas = {}
        self.clientes = {}
    
    @expose
    @oneway
    def add_produto(self, codigo, nome, descricao, preco_inicial, duracao, usuario):
        cliente = self.clientes[usuario]
        produto = Produto(codigo, nome, descricao, preco_inicial, duracao, cliente)
        self.produtos.append(produto)

    @expose
    def get_produtos(self):
        lista_produtos = []
        for produto in self.produtos:
            lista_produtos.append(
                {
                    "codigo": produto.codigo,
                    "nome": produto.nome,
                    "descricao": produto.descricao,
                    "lance": produto.lance,
                    "comprador": produto.comprador,
                    "tempo_final": produto.tempo_final.strftime("%d/%m/%Y %H:%M:%S"),
                }
            )
        
        return lista_produtos

    @expose
    def dar_lance(self, usuario, codigo, valor, signature):
        if usuario not in self.clientes:
            return "Usuário não cadastrado"
        
        if not self.clientes[usuario].chave_publica.verify(
                base64.b64decode(signature['data']),
                "teste".encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            ):
            return "Assinatura inválida"

        for produto in self.produtos:
            if produto.codigo == codigo:
                if produto.set_lance(valor, self.clientes[usuario]):
                    return "Lance efetuado com sucesso! :)"
                return "Lance não aceito. Valor menor que o atual"
        return "Produto não encontrado"
    
    @expose
    def cadastrar_usuario(self, usuario, uri, pem_public_key):
        chave_publica = serialization.load_pem_public_key(
            base64.b64decode(pem_public_key['data']),
        )
        self.clientes[usuario] = Cliente(usuario, uri, chave_publica)

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
                for cliente in produto['clientes_interessados']:
                    cliente.proxy.notificacao(f"Produto {produto['nome']} expirou. O comprador foi {produto['comprador']} com o valor de R$ {produto['lance']}")
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
        