"""Carga didática da Aurora: produtos de moda feminina fitness.

Substitui o `python manage.py seed` (que cria alimentos de supermercado).

Uso, a partir da pasta do projeto, com o ambiente virtual ativado:

    python scripts/seed_roupas.py

O que o script faz:
  1. exige um administrador já criado (python manage.py create-admin);
  2. cria as categorias e o fornecedor fictício, se ainda não existirem;
  3. cadastra os produtos de roupa que ainda não existem (pelo SKU);
  4. registra uma compra inicial para dar entrada no estoque
     (gera uma saída financeira simulada, como o seed original);
  5. DESATIVA os 12 produtos de supermercado do seed antigo, se existirem.
     Eles não são apagados, para preservar o histórico de vendas.

Pode ser executado mais de uma vez: produtos já cadastrados são ignorados.
"""
import os
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)  # o SQLite local usa caminho relativo à pasta do projeto

from sqlalchemy import select  # noqa: E402

from mercado import create_app  # noqa: E402
from mercado.models import Category, Product, Supplier, User  # noqa: E402
from mercado.services.operations import audit, receive_purchase  # noqa: E402

CATEGORIAS = [
    'Tops e Regatas',
    'Leggings e Calças',
    'Shorts e Bermudas',
    'Conjuntos Fitness',
    'Jaquetas e Moletons',
    'Acessórios',
]

# (SKU, nome, categoria, preço de venda, custo, quantidade inicial)
# Roupas são vendidas por unidade (UN). Cada tamanho/cor é um produto próprio,
# pois o estoque do sistema é controlado por produto.
PRODUTOS = [
    ('AUR-TOP-001', 'Top Alta Sustentação Vinho P', 'Tops e Regatas', '89.90', '42.00', '20'),
    ('AUR-TOP-002', 'Top Alta Sustentação Vinho M', 'Tops e Regatas', '89.90', '42.00', '25'),
    ('AUR-TOP-003', 'Top Alta Sustentação Vinho G', 'Tops e Regatas', '89.90', '42.00', '15'),
    ('AUR-TOP-004', 'Regata Dry Fit Mauve M', 'Tops e Regatas', '59.90', '26.00', '20'),
    ('AUR-TOP-005', 'Cropped Canelado Nude P', 'Tops e Regatas', '69.90', '30.00', '18'),

    ('AUR-LEG-001', 'Legging Cintura Alta Vinho M', 'Leggings e Calças', '129.90', '58.00', '25'),
    ('AUR-LEG-002', 'Legging Cintura Alta Vinho G', 'Leggings e Calças', '129.90', '58.00', '18'),
    ('AUR-LEG-003', 'Legging Sem Costura Rosa Antigo P', 'Leggings e Calças', '149.90', '66.00', '15'),
    ('AUR-CAL-001', 'Calça Jogger Moletom Mauve M', 'Leggings e Calças', '139.90', '62.00', '14'),

    ('AUR-SHO-001', 'Short Fitness Cintura Alta Vinho M', 'Shorts e Bermudas', '79.90', '34.00', '20'),
    ('AUR-SHO-002', 'Short Saia Corrida Rosa Antigo M', 'Shorts e Bermudas', '89.90', '38.00', '12'),
    ('AUR-BER-001', 'Bermuda Ciclista Nude M', 'Shorts e Bermudas', '99.90', '44.00', '16'),

    ('AUR-CON-001', 'Conjunto Top + Legging Vinho M', 'Conjuntos Fitness', '199.90', '88.00', '12'),
    ('AUR-CON-002', 'Conjunto Top + Legging Mauve P', 'Conjuntos Fitness', '199.90', '88.00', '10'),

    ('AUR-JAQ-001', 'Jaqueta Esportiva com Zíper Vinho M', 'Jaquetas e Moletons', '189.90', '82.00', '10'),
    ('AUR-JAQ-002', 'Casaco Wrap Ballet Nude P', 'Jaquetas e Moletons', '159.90', '70.00', '8'),
    ('AUR-MOL-001', 'Moletom Cropped Rosa Antigo M', 'Jaquetas e Moletons', '169.90', '74.00', '8'),

    ('AUR-ACE-001', 'Meia Cano Médio Rosa (par)', 'Acessórios', '24.90', '9.00', '40'),
    ('AUR-ACE-002', 'Faixa de Cabelo Esportiva', 'Acessórios', '19.90', '7.00', '30'),
    ('AUR-ACE-003', 'Tapete de Yoga Rosa 6 mm', 'Acessórios', '119.90', '55.00', '10'),
]

# SKUs do seed antigo (alimentos de supermercado)
SKUS_ANTIGOS = ['1001', '1002', '1003', '1004', '2001', '2002',
                '3001', '3002', '4001', '4002', '5001', '5002']

FORNECEDOR = 'Confecções Aurora (fictícia)'


def main():
    app = create_app()
    with app.extensions['db_session']() as db:
        admin = db.scalar(select(User).where(User.role == 'admin', User.active.is_(True)).order_by(User.id))
        if not admin:
            raise SystemExit('Crie o administrador primeiro: python manage.py create-admin')

        # 1) categorias
        cats = {}
        for nome in CATEGORIAS:
            cat = db.scalar(select(Category).where(Category.name == nome)) or Category(name=nome)
            db.add(cat)
            db.flush()
            cats[nome] = cat.id

        # 2) fornecedor
        fornecedor = (db.scalar(select(Supplier).where(Supplier.name == FORNECEDOR))
                      or Supplier(name=FORNECEDOR, contact='Contato de demonstração'))
        db.add(fornecedor)
        db.flush()

        # 3) produtos novos (ignora SKUs já cadastrados)
        linhas = []
        for sku, nome, cat, preco, custo, qtd in PRODUTOS:
            if db.scalar(select(Product.id).where(Product.sku == sku)):
                continue
            p = Product(sku=sku, name=nome, category_id=cats[cat], unit='UN',
                        price=preco, cost=0, stock=0, minimum=5, active=True)
            db.add(p)
            db.flush()
            linhas.append((p.id, qtd, custo))

        # 4) entrada de estoque via compra inicial
        if linhas:
            receive_purchase(db, admin, fornecedor.id, 'CARGA-DIDATICA-ROUPAS', linhas, str(uuid4()))

        # 5) desativa os produtos antigos de supermercado
        desativados = 0
        for p in db.scalars(select(Product).where(Product.sku.in_(SKUS_ANTIGOS), Product.active.is_(True))):
            p.active = False
            desativados += 1
        if desativados:
            audit(db, admin, f'{desativados} produtos de supermercado desativados pela carga de roupas')

        db.commit()
        print(f'{len(linhas)} produtos de roupa cadastrados em {len(CATEGORIAS)} categorias.')
        if linhas:
            print('A compra inicial gera saída financeira simulada.')
        if desativados:
            print(f'{desativados} produtos antigos de supermercado foram desativados (histórico preservado).')


if __name__ == '__main__':
    main()
