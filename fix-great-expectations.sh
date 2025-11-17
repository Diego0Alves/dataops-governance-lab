#!/bin/bash

echo "🔧 Corrigindo problema do Great Expectations..."

# Parar containers
echo "⏹️ Parando containers..."
docker-compose down

# Reconstruir imagem sem cache
echo "🏗️ Reconstruindo imagem Docker..."
docker-compose build --no-cache

# Subir containers
echo "🚀 Iniciando containers..."
docker-compose up -d

# Aguardar containers iniciarem
echo "⏳ Aguardando containers iniciarem..."
sleep 10

# Verificar se Great Expectations está funcionando
echo "🧪 Testando Great Expectations..."
docker exec -it pyspark_aula_container python -c "
import great_expectations as gx
print(f'✅ Great Expectations {gx.__version__} funcionando!')
context = gx.get_context()
print('✅ Data Context inicializado!')
"

echo "✅ Correção concluída!"
echo "🌐 Acesse: http://localhost:8888 (token: tavares1234)"
echo "📓 Execute o notebook: test_great_expectations.ipynb"