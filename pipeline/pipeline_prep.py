import pandas as pd
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import FunctionTransformer

# Função para converter a coluna de data em características numéricas
converter_data = FunctionTransformer(lambda df: pd.to_datetime(df['created_at']).astype(int) / 10 ** 9, validate=True)

# Função para extrair características de texto
extrair_caracteristicas_texto = FunctionTransformer(lambda df: df['name'].str.lower().str.get_dummies(), validate=True)

# Carregar os dados
def carregar_dados():
    return pd.read_csv('pipeline/dados/dados_vendas.csv')

# Criar o pipeline
pipeline = Pipeline(
    [
        ('converter_data', converter_data),
        ('extrair_caracteristicas_texto', extrair_caracteristicas_texto),
        ('imputer', SimpleImputer(strategy='mean')),  # Substitui valores ausentes por média
        ('scaler', StandardScaler()),  # Normaliza características numéricas
        ('one_hot', OneHotEncoder(sparse_output=False, handle_unknown='ignore'))  # One-Hot Encoding para colunas categóricas
    ]
)

# Transformador final que ajusta e transforma os dados de entrada
preprocessor = ColumnTransformer(
    [('numeric_features', StandardScaler(), ['quantity', 'price_x']),
     ('categorical_features', OneHotEncoder(), ['product', 'email'])],
    remainder='drop',  # Descarta colunas não transformadas
    sparse_threshold=0  # Retorna uma matriz densa
)

# Definir o pipeline final
pipeline_final = Pipeline([
    ('load_data', FunctionTransformer(carregar_dados)),
    ('preprocessor', preprocessor),
    ('model', None)  # Placeholder para um modelo de regressão posteriormente
])