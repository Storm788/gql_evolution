# 🧾 Deníček – commity

### Zadání
**6. Evidence majetku, majetek, inventarizační záznam, zápůjčky**  
Projekt pro dva studenty.  
Vyjít z vlastní zkušenosti – seznam věcí, které byly zapůjčeny.  
Zahrnout provedené kontroly evidovaných věcí.

---

## 31. 10. 2025 | Release 1.1
Regenerace `systemdata.json` a `systemdata.backup.json`, dočasný formát výstupu.  
Kontrola exportu – generátor občas duplikoval pozvánky a vytvářel sirotky bez vazby.  
Po opravě a testu export proběhl bez chyb.

---

## 29. 10. 2025 | Stabilní build 1.0
Refaktor `src/DBFeeder.py`, sladění `main.py` s docker orchestrace.  
Hodinové porovnávání JSONů – ručně dohledané rozdíly v timezone offsetech, které házely chyby při importu.

---

## 27. 10. 2025 | Správa majetku
Kompletní CRUD systém pro správu assetů.  
Nové modely, dotazy, testy.  
Problém: napojení inventárních záznamů na skupinové vlastnictví a konzistence při autorizaci.

---





