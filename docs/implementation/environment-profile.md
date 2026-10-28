# Perfil distribuído do ambiente

O perfil público da interface é injetado quando o contêiner frontend inicia. Isso
permite que a imagem pré-construída receba os mesmos valores `PUBLIC_MODE` e
`PATTERNS_ENABLED` da API. Em desenvolvimento com Vite, os valores `VITE_*` de
build continuam como fallback. `VITE_API_URL` usa por padrão a origem atual, que
é encaminhada pelo Nginx/Caddy à API; quando configurada, deve ser uma origem HTTPS
(HTTP só é aceito para localhost em desenvolvimento).

O Compose raiz `docker-compose.yml` também passa as três variáveis de runtime ao
frontend e mantém os argumentos de build alinhados, evitando que o fallback da
imagem esconda divergência com a API.

Antes de iniciar o Compose de produção, renderize e valide a configuração sem
subir serviços:

```sh
docker compose \
  --file infra/docker-compose.prod.yml \
  --file infra/docker-compose.prod.images.yml \
  pull api frontend

python3 infra/scripts/profile-preflight.py \
  --compose-file infra/docker-compose.prod.yml \
  --compose-file infra/docker-compose.prod.images.yml \
  --production \
  --verify-images
```

`--verify-images` exige os rótulos
`org.brasil-em-rede.frontend-runtime-config=v1` e
`org.brasil-em-rede.api-source-catalog=v1` nas imagens frontend e API já obtidas.
Assim, imagens antigas sem o entrypoint de perfil ou sem o contrato de catálogo
falham antes da subida. O `deploy.sh` executa o preflight depois do pull/build e
antes de `compose up`; esta validação não inicia serviços.

O preflight verifica a igualdade das flags da API e da interface, os valores de
produção para `APP_ENV`, `AUTH_COOKIE_SECURE`, `NEO4J_PASSWORD`, `JWT_SECRET_KEY`,
`CORS_ORIGINS`, domínio e URL da API. A saída contém somente aprovação ou nomes de
campos inválidos; o JSON renderizado pelo Compose, que contém valores interpolados,
fica em memória e não é impresso. Use `.env` local não versionado para os valores
reais. Testes podem fornecer um arquivo sintético com `--env-file`.

`PUBLIC_ALLOW_PERSON`, `PUBLIC_ALLOW_ENTITY_LOOKUP` e
`PUBLIC_ALLOW_INVESTIGATIONS` são controles de autorização do servidor e são
validados somente na configuração da API. A interface pode ocultar rotas, mas isso
não concede nem restringe acesso a dados por si só.

O readiness da API continua distinto do endpoint `/health`: verifica que o
catálogo carregável está presente e que a API responde conectada ao Neo4j. Isso não
certifica acesso a fontes, qualidade dos dados nem dimensão de uma partição real.

`infra/scripts/seed-dev.sh` cria um projeto e volume Compose próprios, mas
`scripts/bootstrap_public_demo.sh` ainda inicia o Compose compartilhado antes de
chamar seed e pode executar ETL no banco configurado. Não use esse bootstrap como
atalho para demonstração até uma demanda própria revisar e isolar esse contrato.
Nenhum seed, reset, aquisição, migração ou restore real faz parte do preflight.
