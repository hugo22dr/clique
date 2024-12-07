
# Gerenciador de Navegadores com Cliques Sincronizados

## **Descrição**
Este programa permite o gerenciamento e interação simultânea em navegadores distintos, realizando cliques precisos e sincronizados em elementos definidos pelo usuário. Ideal para cenários que exigem tolerância a falhas e operações coordenadas em múltiplas instâncias.

## **Principais Funcionalidades**
- **Cliques Simultâneos**: Sincronização com desvios mínimos entre as interações.
- **Modularidade**: Componentes separados para logs, memória, CPU e cliques.
- **Resiliência**: Continuidade mesmo com falhas de sessão ou alterações no DOM.
- **Flexibilidade**: Adição de links e XPaths em tempo real.

## **Comandos Disponíveis**
1. `new link`: Configura novos links nos navegadores.
2. `add`: Adiciona XPaths para elementos.
3. `click`: Executa cliques sincronizados.
4. `localize`: Localiza elementos configurados.
5. `exit`: Encerra o programa.

## **Requisitos**
- Python 3.8 ou superior.
- Dependências:
  ```
  selenium
  undetected-chromedriver
  psutil
  colorama
  ```

## **Instalação**
1. Clone o repositório:
   ```
   git clone <url-do-repositorio>
   cd <nome-do-repositorio>
   ```
2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
3. Execute o programa:
   ```
   python main.py
   ```

## **Recomendações de Hardware**
- **CPU**: Ryzen 9 5900X ou equivalente.
- **RAM**: 32 GB.
- **Armazenamento**: SSD NVMe.

## **Licença**
Este projeto é licenciado sob a MIT License.
