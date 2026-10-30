# Bootstrap de demonstração pública com segurança

`scripts/bootstrap_public_demo.sh` não inicia serviços nem grava dados por padrão. Sem argumentos, com `--help` ou com `--doctor`, limita-se a mostrar ajuda ou executar o diagnóstico somente leitura do contrato completo. O diagnóstico pode retornar erro quando os arquivos de entrada locais não existem; isso não inicia aquisição.

O único caminho de escrita exposto pelo wrapper é explicitamente nomeado e confirmado:

```bash
DEMO_NEO4J_PASSWORD='(defina localmente)' scripts/bootstrap_public_demo.sh --seed-isolated --i-understand-isolated-demo
```

Esse caminho delega exclusivamente a `infra/scripts/seed-dev.sh`, que cria um projeto Compose e volume novos com identificador aleatório. O wrapper não lê `.env`, não usa senha padrão, não executa Compose legado, não faz download nem ETL. Variáveis herdadas `NEO4J_URI`, `COMPOSE_PROJECT_NAME`, `DOWNLOAD` e `PIPELINES` são removidas na fronteira da delegação. Não passe segredos em argumentos ou relatórios.

Opções antigas `--profile`, `--pipelines`, `--download` e `--no-download` são rejeitadas, assim como opções desconhecidas ou combinações/marcadores incompletos. Não há modo `full`: a documentação anterior sugeria download e execução ETL, mas os scripts `scripts/download_comprasnet.py` e `scripts/download_datasus.py` não existem. O contrato mantém esses IDs e entradas `file_manifest`; suas justificativas agora deixam claro que dependem de arquivos locais revisados e não certificam aquisição.

Os testes substituem a fronteira do seeder por fixture temporária; não iniciam Docker, seed real, aquisição, ETL ou reset.
