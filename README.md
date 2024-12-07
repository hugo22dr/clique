# Programa de Sincronização de Cliques com Módulo Kernel

## **Visão Geral**

Este projeto gerencia múltiplos navegadores para realizar **cliques simultâneos com precisão**. Ele foi desenvolvido para **Linux** e utiliza um **módulo kernel personalizado** para garantir sincronização em nível de hardware.

---

## **Principais Funcionalidades**

1. **Sincronização Precisa de Cliques**  
   - Utiliza o módulo kernel `click_sync_kernel` para coordenar cliques simultâneos com mínimo desvio.

2. **Gerenciamento Avançado de Sistema**  
   - Otimização de CPU, memória e prioridade dos processos.
   - Configuração de swappiness e afinidade de CPU.

3. **Interatividade em Tempo Real**  
   - Comandos disponíveis no terminal:
     - `new link` — Configura novos links nos navegadores.
     - `add` — Adiciona novos XPaths dinamicamente.
     - `click` — Executa cliques sincronizados nos elementos configurados.
     - `localize` — Localiza os elementos no navegador configurado.

4. **Resiliência e Robustez**  
   - Tolerância a alterações no **DOM** ou erros temporários nos navegadores.

---

## **Pré-requisitos**

- **Sistema Operacional**: Linux  
- **Python**: Versão 3.8+  
- **Dependências**:  
   - `selenium`, `undetected-chromedriver`, `psutil`, `colorama`

---

## **Instalação**

1. Clone o repositório e entre na pasta:
   ```bash
   git clone https://github.com/hugo22dr/clique
   cd clique
