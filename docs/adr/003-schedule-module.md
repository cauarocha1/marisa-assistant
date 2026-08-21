# ADR 003: Módulo explícito para dedução da grade horária

## Status

Aceito

## Contexto

Os critérios de aceite da Seção 5 exigem testes para validade da grade,
disciplinas em dias múltiplos e situações que devem pedir confirmação. O
contrato original descrevia a política em `AGENTS.md`, mas não definia um
módulo de código para a dedução.

## Decisão

Adicionar `agent/schedule.py` com a função pura `deduce_class_time`. A função
mantém a grade vigente e retorna `None` sempre que a data estiver fora do
período válido ou não houver correspondência inequívoca.

## Consequências

A política fica isolada, determinística e testável sem rede ou credenciais.
Quando um novo semestre começar, a grade e o intervalo devem ser atualizados
conforme o procedimento do `RUNBOOK.md`.
