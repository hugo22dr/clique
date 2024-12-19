# Click Sync - Sistema de Sincronização Precisa de Cliques

## Visão Geral
Click Sync é um sistema de alta precisão projetado para executar cliques simultâneos em múltiplos navegadores com desvio próximo a zero. Desenvolvido especificamente para testes de segurança e análise de vulnerabilidades, o sistema utiliza otimizações a nível de kernel para garantir sincronização precisa em escala de nanosegundos.

### Características Principais
- Sincronização de cliques com precisão de nanosegundos
- Suporte a múltiplos navegadores e contextos
- Otimização específica para processadores AMD Ryzen
- Sistema de barreiras de sincronização em três fases
- Logging detalhado com análise de timestamps

## Requisitos do Sistema

### Hardware Recomendado
- Processador: AMD Ryzen (otimizado para série 5000+)
- Memória RAM: 16GB+ 
- Armazenamento: SSD NVMe
- Sistema Operacional: Linux (testado em Fedora)

### Dependências
- Python 3.8+
- Selenium WebDriver
- Chrome/Chromium
- Módulos do kernel Linux
- Privilégios root para otimizações de kernel

## Instalação

### 1. Preparação do Sistema
```bash
# Instale as dependências necessárias
sudo dnf install gcc kernel-devel python3-devel chromium-chromedriver

# Configure as permissões de tempo real
echo 'kernel.sched_rt_runtime_us=-1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 2. Instalação do Módulo Kernel
```bash
# Compile o módulo
cd modules/click_sync
make

# Instale o módulo
sudo insmod click_sync.ko

# Verifique a instalação
lsmod | grep click_sync
```

### 3. Instalação do Pacote Python
```bash
# Instale o pacote
pip install -e .
```

## Estrutura do Projeto
```
/clique/
├── modules/
│   ├── click_sync/         # Módulo kernel
│   ├── click_sync.c        
│   └── click_sync_wrapper.c
├── src/
│   ├── click_manager/      # Gerenciamento de cliques
│   ├── commands/           # Comandos do programa
│   ├── main/              # Componentes principais
│   ├── memory/            # Gerenciamento de memória
│   ├── navegador/         # Interação com navegadores
│   └── sistema/           # Gerenciamento do sistema
└── setup.py
```

## Uso

### Comandos Básicos
- `new link`: Define URLs para os navegadores
- `add`: Adiciona XPaths para elementos
- `localize`: Verifica elementos nos navegadores
- `click`: Executa cliques sincronizados
- `exit`: Encerra o programa

### Exemplo de Uso
```python
# Inicie o programa
python main.py

# Configure links
> new link
Digite o novo link para o navegador 1: https://site1.com
Digite o novo link para o navegador 2: https://site2.com

# Adicione elementos
> add
Digite um novo XPath para o navegador 1: //button[@id='submit']
Digite um novo XPath para o navegador 2: //input[@type='submit']

# Execute cliques sincronizados
> click
```

## Componentes Principais

### 1. Módulo Kernel (click_sync)
- Implementa sincronização precisa usando TSC
- Gerencia barreiras de sincronização
- Otimiza scheduling de threads
- Implementa controle de tempo real

### 2. Gerenciador de Cliques
- Coordena operações de clique
- Implementa executor atômico
- Gerencia timestamps precisos
- Analisa desvios de sincronização

### 3. Gerenciador de Navegadores
- Controla instâncias Selenium
- Gerencia estados dos navegadores
- Implementa localização resiliente
- Otimiza carregamento de páginas

### 4. Sistema de Memória
- Implementa lock de memória
- Otimiza uso de cache
- Gerencia prioridades I/O
- Configura scheduling RT

## Segurança e Considerações

### Avisos de Segurança
- Use apenas para testes autorizados
- Obtenha permissão antes de testar sites
- Evite sobrecarga em servidores
- Respeite políticas de segurança

### Limitações Conhecidas
- Requer privilégios root
- Otimizado para AMD Ryzen
- Depende de kernel Linux
- Requer Chrome/Chromium (devido ao undetected-chromedriver)

O sistema foi desenvolvido para manter a precisão e sincronização independentemente de:
- Complexidade do DOM
- Framework utilizado no site
- Estado de carregamento da página
- Tipo de elemento a ser clicado
- Quantidade de JavaScript/requisições
- Animações ou transições

Os testes já demonstraram essa independência de contexto, com desvios consistentemente baixos (4-6 nanosegundos).

## Debugging e Logs

### Sistema de Logging
O sistema fornece logs detalhados com:
- Timestamps precisos
- Análise de desvios
- Estados de sincronização
- Métricas de performance

### Exemplo de Log
```
🔬 Análise Precisa de Timestamps:
  ⚡ Pre-Atomic (Driver ID):
    ⏱️ Monotonic: 24009114671290 ns
    ⚙️ Process Time: 206499813 ns
    🧵 Thread Time: 170967264 ns
```

### Diagnóstico
Use os scripts fornecidos para diagnóstico:
- `diagnose.sh`: Verifica estado do sistema
- `verify_click_sync.sh`: Valida módulo kernel

### Troubleshooting Comum
1. Erro de Privilégios
   - Verifique se está executando como root
   - Confirme as permissões do dispositivo

2. Módulo Kernel não Carrega
   - Verifique compatibilidade do kernel
   - Confirme se os headers estão instalados

3. Falha na Sincronização
   - Verifique carga do sistema
   - Confirme prioridade RT
   - Valide configurações de CPU

4. Elementos não Encontrados
   - Verifique XPaths
   - Confirme carregamento da página
   - Valide estado do DOM

## Performance

### Métricas Típicas
- Desvio médio: 4-6 nanosegundos
- Desvio máximo: < 10 nanosegundos
- Tempo de sincronização: < 1 microssegundo
- Precisão de timestamp: nanosegundos

### Otimizações
- Afinidade de CPU por CCX
- Prioridade RT para threads críticas
- Lock de memória para performance
- Barreiras otimizadas por hardware
- Sincronização TSC

## Contribuição
1. Fork o repositório
2. Crie um branch para features
3. Faça commit das alterações
4. Push para o branch
5. Crie um Pull Request

## Licença
Este projeto está licenciado sob a GPL v3.

## Suporte
Para suporte e dúvidas:
1. Abra uma issue no GitHub
2. Documente o problema detalhadamente
3. Inclua logs relevantes
4. Forneça informações do sistema

## Créditos
Desenvolvido para testes de segurança e análise de vulnerabilidades.

## Changelog
### v1.0.0
- Implementação inicial
- Suporte a AMD Ryzen
- Sistema de barreiras
- Logging preciso
