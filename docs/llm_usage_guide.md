# Przykład użycia raportu LLM do naprawy kodu

## Prompt dla LLM:

```
Jestem ekspertem od jakości kodu Python. Pomóż mi naprawić błędy w projekcie exef-pl/app.

Oto raport z analizy kodu:

[WKLEJ TREŚĆ PLIKU 20260128_221849.llm.md TUTAJ]

### Proszę o:

1. **Analizę priorytetów:** 
   - Czy wszystkie 1117 plików wymagają formatowania Black?
   - Czy są jakieś krytyczne błędy wymagające natychmiastowej uwagi?

2. **Plan naprawy:**
   - Krok 1: Uruchomienie formatowania Black na całym projekcie
   - Krok 2: Weryfikacja, czy formatowanie nie zepsuło działania kodu
   - Krok 3: Ponowne uruchomienie raportu

3. **Potencjalne ryzyka:**
   - Czy formatowanie Black może wpłynąć na działanie aplikacji?
   - Czy należy utworzyć backup przed zmianami?

4. **Dodatkowe sugestie:**
   - Czy warto dodać pre-commit hooks dla automatycznego formatowania?
   - Jakie inne narzędzia warto skonfigurować?

Zacznijmy od kroku 1. Czy mogę bezpiecznie uruchomić `black .` w tym projekcie?
```

## Alternatywny prompt (krótszy):

```
Potrzebuję pomocy z naprawą kodu Python w projekcie exef-pl/app.

Raport pokazuje 1117 plików wymagających formatowania Black i brak krytycznych błędów.

Pytania:
1. Czy mogę bezpiecznie uruchomić `black .` na całym projekcie?
2. Jakie są najlepsze praktyki przy masowym formatowaniu kodu?
3. Czy powinienem najpierw zrobić commit zmian?

Proszę o krótkie instrukcje krok po kroku.
```

## Wskazówki dla LLM:

- ✅ **Dodaj kontekst:** "Jestem deweloperem pracującym nad projektem..."
- ✅ **Określ cel:** "Chcę naprawić błędy jakości kodu..."
- ✅ **Podaj priorytety:** "Zacznij od krytycznych błędów, potem formatowanie..."
- ✅ **Poproś o plan:** "Proszę o plan krok po kroku..."
- ❌ **Nie przekraczaj limitu tokenów:** Dziel duże raporty na części
- ❌ **Nie kopiuj całego raportu:** Skup się na najważniejszych sekcjach

## Formatowanie odpowiedzi od LLM:

Oczekiwana struktura odpowiedzi:
1. **Podsumowanie sytuacji** (2-3 zdania)
2. **Plan działania** (numerowana lista)
3. **Komendy do wykonania** (w code blocks)
4. **Ostrzeżenia i ryzyka** (jeśli są)
5. **Następne kroki** (co robić dalej)
