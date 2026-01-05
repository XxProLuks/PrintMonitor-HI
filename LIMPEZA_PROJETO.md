# 🧹 Plano de Limpeza do Projeto

## 📋 Resumo da Auditoria

A auditoria completa identificou os seguintes pontos que precisam de atenção:

### ✅ **Status Geral: BOM**
- Projeto bem estruturado
- Código funcional
- Documentação extensa
- Pronto para produção

### ⚠️ **Melhorias Recomendadas**

---

## 🔴 PRIORIDADE ALTA

### 1. Módulos de IA Referenciando Custos Removidos

**Problema:** 
- `ia_previsao_custos.py` tenta calcular custos que não existem mais
- Rota `/api/ia/previsao-custos` pode falhar

**Solução:**
- Opção A: Remover módulo e rota completamente
- Opção B: Atualizar para trabalhar sem custos (usar apenas páginas/folhas)

**Arquivos Afetados:**
- `serv/modules/ia_previsao_custos.py`
- `serv/servidor.py` (rota `/ia/previsao-custos`)

### 2. Função `custo_unitario_por_data` Deprecated

**Problema:**
- Função ainda existe mas sistema de custos foi removido
- Ainda usada em algumas rotas (setores, etc.)

**Solução:**
- Remover função ou atualizar para retornar 0
- Atualizar rotas que ainda a usam

**Arquivos Afetados:**
- `serv/servidor.py` (função `custo_unitario_por_data`)
- `serv/servidor.py` (rota `/setores`)
- `serv/servidor.py` (rota `/impressoras/export`)

### 3. Arquivos Duplicados

**Problema:**
- `scanner_impressoras.py` (raiz) duplicado
- `agent/scanner_rede_impressoras.py` (mais completo)

**Solução:**
- Remover `scanner_impressoras.py` da raiz
- Manter apenas `agent/scanner_rede_impressoras.py`

---

## 🟡 PRIORIDADE MÉDIA

### 4. Arquivos de Teste na Raiz

**Arquivos:**
- `test_project.py`
- `test_endpoints.py`
- `test_admin_impressoras.py`
- `simular_impressoes.py`

**Solução:**
- Criar pasta `tests/`
- Mover arquivos para `tests/`
- Ou remover se não forem mais necessários

### 5. Scripts Redundantes

**Arquivos:**
- `cadastrar_impressoras_manual.py` - Funcionalidade já existe no admin
- `importar_impressoras_csv.py` - Funcionalidade já existe no admin

**Solução:**
- Verificar se são realmente redundantes
- Remover se não forem mais necessários

### 6. Imports Não Utilizados

**Verificar:**
- `ctypes` e `ctypes.wintypes` em `servidor.py`
- Imports de módulos de IA não utilizados

---

## 🟢 PRIORIDADE BAIXA

### 7. Documentação Duplicada

**Arquivos:**
- Múltiplos arquivos .md com informações similares
- `AUDITORIA_PROJETO.md` vs `AUDITORIA_COMPLETA_2024.md`

**Solução:**
- Consolidar documentação
- Manter apenas versão mais atualizada

### 8. Otimização de Código

**Melhorias:**
- Refatorar queries SQL duplicadas
- Centralizar lógica comum
- Adicionar type hints em mais funções

---

## 📝 CHECKLIST DE EXECUÇÃO

### Fase 1: Remover Referências a Custos
- [ ] Atualizar ou remover `ia_previsao_custos.py`
- [ ] Remover/atualizar rota `/ia/previsao-custos`
- [ ] Remover função `custo_unitario_por_data` ou atualizar
- [ ] Atualizar rotas que usam `custo_unitario_por_data`

### Fase 2: Limpar Arquivos Duplicados
- [ ] Remover `scanner_impressoras.py` da raiz
- [ ] Verificar se `agent/scanner_rede_impressoras.py` está completo

### Fase 3: Organizar Arquivos
- [ ] Criar pasta `tests/`
- [ ] Mover arquivos de teste
- [ ] Remover scripts redundantes

### Fase 4: Limpar Código
- [ ] Remover imports não utilizados
- [ ] Verificar módulos de IA não utilizados
- [ ] Consolidar documentação

---

## 🚀 COMO EXECUTAR

### Opção 1: Limpeza Manual
Siga o checklist acima manualmente.

### Opção 2: Script Automatizado
Execute o script de limpeza (a ser criado):
```bash
python limpar_projeto.py
```

---

## ⚠️ AVISOS

1. **Backup antes de remover arquivos**
2. **Testar após cada mudança**
3. **Verificar se funcionalidades ainda funcionam**
4. **Atualizar documentação**

---

**Última atualização:** 2024-12-05

