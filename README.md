# Fatura Itaú PDF to CSV Converter 📄➡️📊

Conversor de faturas do cartão de crédito Itaú em formato PDF para CSV/Excel. Uma aplicação web simples construída com Streamlit que extrai transações de faturas PDF e gera planilhas organizadas.

## 🎯 Funcionalidades

- ✅ **Extração automática de transações** de PDFs da fatura Itaú
- ✅ **Interface web intuitiva** com Streamlit
- ✅ **Geração de CSV** pronto para Excel/Google Sheets
- ✅ **Cálculo automático** do total dos lançamentos
- ✅ **Cópia direta** para área de transferência
- ✅ **Preview dos dados** antes do download
- ✅ **Filtros inteligentes** para remover seções irrelevantes (compras parceladas futuras, etc.)

## 🚀 Como usar

### 1. Instalação

Clone o repositório:
```bash
git clone https://github.com/joaopenedo/Fatura-Itau-PDF-to-CSV.git
cd Fatura-Itau-PDF-to-CSV
```

Instale as dependências usando o `uv`:
```bash
uv sync
```

Ou se preferir usar pip tradicional:
```bash
pip install -r requirements.txt
```

### 2. Execução

Execute a aplicação:
```bash
uv run streamlit run app.py
```

Ou se estiver usando pip tradicional:
```bash
streamlit run app.py
```

A aplicação será aberta no seu navegador em `http://localhost:8501`

### 3. Uso

1. **Faça upload** do arquivo PDF da sua fatura Itaú
2. **Clique em "Processar PDF"** para extrair os dados
3. **Visualize o preview** das transações extraídas
4. **Baixe o CSV** ou **copie diretamente** para o Excel

## 📋 Formato de saída

O CSV gerado contém as seguintes colunas:

| Coluna | Descrição | Exemplo |
|--------|-----------|---------|
| `Data` | Data da transação | `15/08` |
| `Estabelecimento` | Nome do estabelecimento/serviço | `PADARIA DO JOAO` |
| `Valor (R$)` | Valor da transação | `25,50` |
| `Passada` | Número da passada de processamento | `1` |
| `Pagina` | Página do PDF onde foi encontrada | `2` |
| `Coluna` | Coluna da página onde foi encontrada | `1` |

## 🔧 Estrutura do projeto

```
├── app.py           # Interface Streamlit principal
├── parser.py        # Motor de extração de dados do PDF
├── requirements.txt # Dependências Python (pip)
├── pyproject.toml   # Configuração do projeto (uv)
└── README.md        # Este arquivo
```

## 📝 Principais componentes

### `app.py`
- Interface web com Streamlit
- Upload de arquivos PDF
- Preview e download dos dados
- Funcionalidade de cópia para área de transferência

### `parser.py`
- Extração de texto do PDF usando `pdfplumber`
- Regex para identificar transações
- Filtros para remover seções irrelevantes
- Processamento e limpeza dos dados

## 🔍 Funcionalidades avançadas

### Filtros automáticos
- Remove seção "Compras parceladas - próximas faturas"
- Remove seção "Fique atento aos encargos"
- Remove informações de limite de crédito
- Filtra apenas transações válidas

### Processamento inteligente
- Detecta automaticamente o número do cartão
- Normaliza valores monetários
- Trata caracteres especiais e acentos
- Suporte a múltiplos cartões na mesma fatura

## ⚙️ Requisitos técnicos

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recomendado para gerenciamento de dependências)

## 🤝 Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para:

1. Fazer fork do projeto
2. Criar uma branch para sua funcionalidade (`git checkout -b feature/nova-funcionalidade`)
3. Commitar suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Fazer push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abrir um Pull Request

## 📄 Licença

Este projeto está sob a licença <TODO>. Veja o arquivo `LICENSE` para mais detalhes.

## 🐛 Problemas conhecidos

- Requer que o PDF tenha texto extraível (não funciona com PDFs apenas de imagem)

## 📞 Suporte

Se encontrar algum problema ou tiver sugestões, por favor:

1. Verifique se o problema já foi reportado nas [Issues](https://github.com/joaopenedo/Fatura-Itau-PDF-to-CSV/issues)
2. Abra uma nova issue com detalhes do problema
3. Inclua uma amostra do PDF (sem dados sensíveis) se possível

---

**Desenvolvido com ❤️ para facilitar o controle financeiro pessoal**
