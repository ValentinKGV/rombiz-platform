# RomBiz Intelligence — Ghid de Utilizare

> **Pentru utilizatorul de rând** — tot ce trebuie să știi pentru a folosi platforma, pas cu pas.  
> Versiune: 1.0 · Actualizat: Martie 2026

---

## Cuprins

1. [Ce este RomBiz Intelligence?](#1-ce-este-ro mbiz-intelligence)
2. [Cum mă înregistrez?](#2-cum-mă-înregistrez)
3. [Cum mă autentific?](#3-cum-mă-autentific)
4. [Pagina principală (Dashboard)](#4-pagina-principală-dashboard)
5. [Cum caut o firmă?](#5-cum-caut-o-firmă)
6. [Profilul unei companii — ce găsesc acolo?](#6-profilul-unei-companii--ce-găsesc-acolo)
7. [Scorul de risc — ce înseamnă A, B, C, D, E?](#7-scorul-de-risc--ce-înseamnă-a-b-c-d-e)
8. [Portofolii — cum monitorizez mai multe firme](#8-portofolii--cum-monitorizez-mai-multe-firme)
9. [Alerte — cum primesc notificări automate](#9-alerte--cum-primesc-notificări-automate)
10. [Rapoarte — cum generez și descarc un raport](#10-rapoarte--cum-generez-și-descarc-un-raport)
11. [ESG — ce înseamnă și cum îl citesc](#11-esg--ce-înseamnă-și-cum-îl-citesc)
12. [Fraud Graph — detectarea legăturilor suspecte](#12-fraud-graph--detectarea-legăturilor-suspecte)
13. [SEAP — licitații publice](#13-seap--licitații-publice)
14. [Firme Noi](#14-firme-noi)
15. [RedBill — datorii restante](#15-redbill--datorii-restante)
16. [Asistentul AI](#16-asistentul-ai)
17. [Setări și profil personal](#17-setări-și-profil-personal)
18. [Trucuri și scurtături utile](#18-trucuri-și-scurtături-utile)
19. [Întrebări frecvente (FAQ)](#19-întrebări-frecvente-faq)
20. [Glosar de termeni](#20-glosar-de-termeni)

---

## 1. Ce este RomBiz Intelligence?

**RomBiz Intelligence** este o platformă care colectează automat date despre **toate firmele din România** din surse publice oficiale (ANAF, ONRC, BPI, SEAP, Portal Just și altele) și le prezintă într-un format clar, ușor de înțeles.

### Cu ce te ajută?

- **Verifici o firmă** înainte să faci afaceri cu ea — are datorii? e în insolvență? are litigii?
- **Monitorizezi clienții și furnizorii** — primești notificări automate dacă se schimbă ceva important
- **Găsești firme noi** care să devină clienți sau parteneri
- **Generezi rapoarte profesionale** pentru due diligence, bănci sau investitori
- **Urmărești licitații publice** câștigate sau active

### De ce este util?

Fără RomBiz, ar trebui să verifici manual ANAF, ONRC, BPI, Portal Just — ore de muncă pentru o singură firmă. RomBiz face totul automat, în câteva secunde.

---

## 2. Cum mă înregistrez?

### Pasul 1 — Accesează platforma

Deschide browser-ul (Chrome, Firefox sau Edge) și mergi la adresa platformei.

### Pasul 2 — Apasă „Creează cont"

Pe pagina de login, apasă linkul **„Creează cont"** sau **„Register"** aflat în partea de jos a formularului.

### Pasul 3 — Completează formularul

| Câmp | Ce introduci |
|---|---|
| **Email** | Adresa ta de email (va fi username-ul) |
| **Parolă** | Minim 8 caractere — alege una sigură |
| **Prenume** | Prenumele tău |
| **Nume** | Numele de familie |
| **Organizație** | Numele firmei sau persoanei pentru care lucrezi |

### Pasul 4 — Apasă „Înregistrare"

Contul este creat imediat. Ești redirecționat automat la pagina de login.

> **Notă:** Un administrator poate fi nevoit să activeze contul tău dacă organizația are configurată aprobare manuală.

---

## 3. Cum mă autentific?

1. Mergi la pagina de login a platformei
2. Introdu **Email-ul** și **Parola**
3. Apasă **„Intră în Univers"** (sau „Login")
4. Ești dus automat la **Dashboard**

### Sesiunea mea expiră?

Da. Token-ul de acces durează **30 de minute**, dar platforma îl reîmprospătează automat cât timp ești activ. Dacă stai inactiv mai mult timp, ești redirecționat automat la login.

### Cum mă deconectez?

Apasă butonul **Logout** (iconița ușă 🚪) din bara laterală din stânga, în josul meniului.

---

## 4. Pagina principală (Dashboard)

Imediat după login, pagina principală îți arată o privire de ansamblu:

### Ce văd pe Dashboard?

```
┌─────────────────────────────────────────────────┐
│  Total Companii   │ Active │ Cu Datorii │ Insolvente │
├─────────────────────────────────────────────────┤
│  Distribuție Risc (grafic Pie A-B-C-D-E)        │
├─────────────────────────────────────────────────┤
│  Top Sectoare (Bar Chart CAEN)                  │
├─────────────────────────────────────────────────┤
│  Alerte Recente (ultimele 5)                    │
└─────────────────────────────────────────────────┘
```

### Ce înseamnă indicatorii cheie?

| Indicator | Descriere |
|---|---|
| **Total Companii** | Câte firme există în baza de date |
| **Companii Active** | Firme cu stare ACTIVA la ONRC |
| **Cu Datorii** | Firme care apar în AEGRM (datorii la stat) |
| **Insolvente** | Firme cu procedură de insolvență deschisă în BPI |

### Notificări în timp real

Platforma folosește WebSocket pentru a te notifica **instant** (fără să dai refresh) când:
- Apare o alertă nouă pentru o firmă din portofoliu
- Se finalizează un raport generat de tine
- Se schimbă ceva important la o firmă monitorizată

Notificările apar ca **mesaje pop-up** în colțul din dreapta sus al ecranului.

---

## 5. Cum caut o firmă?

### Metoda 1 — Căutare rapidă din sidebar

1. Apasă pe **„Căutare"** în meniul din stânga
2. Scrie în câmpul de căutare: denumirea firmei, CUI-ul sau nr. de la Registrul Comerțului
3. Apasă **Enter**

### Metoda 2 — Shortcut de la tastatură

Apasă **`Ctrl + K`** (sau `Cmd + K` pe Mac) **de oriunde** în aplicație pentru a deschide rapid căutarea.

### Ce pot scrie în câmpul de căutare?

- **Denumire** — ex: `Rompetrol`, `Tech Solutions` (parțial merge)
- **CUI** — ex: `14399840` sau `RO14399840`
- **Nr. Reg. Com.** — ex: `J40/1234/2020`

### Filtre avansate

Apasă **„Filtre"** pentru a rafina rezultatele:

| Filtru | Exemple |
|---|---|
| **Județ** | Cluj, București, Ilfov |
| **Cod CAEN** | 6201 (IT), 4120 (Construcții) |
| **Stare** | ACTIVA, INACTIVA, RADIATA |
| **Rating risc** | A, B, C, D, E |
| **Plătitor TVA** | Da / Nu |
| **Cu datorii** | Da / Nu |
| **An înființare** | Ex: 2010 – 2020 |

### Cum interpretez rezultatele?

Fiecare firmă din rezultate afișează:

| Coloană | Ce înseamnă |
|---|---|
| **Denumire** | Numele firmei (click = deschide profilul) |
| **CUI** | Codul unic de identificare fiscală |
| **Județ** | Localizare |
| **CAEN** | Codul activității principale |
| **Stare** | ACTIVA / INACTIVA / RADIATA |
| **Rating** | A (verde) → E (roșu) — risc calculat |

---

## 6. Profilul unei companii — ce găsesc acolo?

Apasă pe denumirea unei firme din rezultatele căutării pentru a deschide **profilul complet**.

### Informații generale (sus)

Chiar în fruntea paginii găsești:
- Denumire oficială, CUI, Nr. Registrul Comerțului
- Forma juridică (SRL, SA, PFA, RA, etc.)
- **Stare:** ACTIVA / INACTIVA / RADIATA (cu culori)
- Data înregistrării la ONRC
- Cod CAEN și descrierea activității
- Capital social
- Adresă completă

### Butoane de acțiune rapidă

| Buton | Ce face |
|---|---|
| **+ Portofoliu** | Salvează firma într-un portofoliu de monitorizare |
| **Raport** | Generează un raport PDF/Excel |
| **Alertă** | Setează o notificare pentru modificări |

### Tab-urile disponibile

Profilul este organizat pe **tab-uri** (secțiuni). Apasă pe fiecare pentru a vedea detalii:

---

#### Tab: Financiar

Afișează **bilanțurile anuale** raportate la ANAF:

| Coloană | Descriere |
|---|---|
| **An fiscal** | Anul raportării |
| **Cifra de afaceri** | Venituri totale din vânzări |
| **Profit net** | Profit sau pierdere netă |
| **Nr. angajați** | Salariați declarați |
| **Total datorii** | Datorii totale (furnizori + bănci + stat) |
| **Capital propriu** | Averea netă a firmei |

**Graficele** de mai jos arată evoluția în timp a cifrelor principale. O tendință descendentă a profitului sau o creștere bruscă a datoriilor sunt semnale de atenție.

---

#### Tab: Persoane

Lista **asociaților și administratorilor** actuali și istorici:

| Câmp | Descriere |
|---|---|
| **Tip** | Administrator / Asociat / Director |
| **Nume** | Numele complet |
| **Cotă** | Procentul de participare la capital (pentru asociați) |
| **Din** | Data la care a preluat funcția |
| **Până** | Data la care a ieșit (gol = activ) |
| **Activ** | ✅ = activ în prezent |

> **Sfat:** Dacă o firmă și-a schimbat administratorul de mai multe ori în scurt timp, poate fi un semnal de risc comportamental.

---

#### Tab: Insolvență

Dosarele din **BPI (Buletinul Procedurilor de Insolvență)**:

| Câmp | Descriere |
|---|---|
| **Nr. Dosar BPI** | Numărul publicației oficiale |
| **Tip procedură** | Insolvență / Reorganizare / Faliment / Lichidare |
| **Tribunal** | Instanța care judecă cazul |
| **Practician** | Administratorul / lichidatorul judiciar |
| **Data deschiderii** | Când a început procedura |
| **Status** | Activ / Finalizat |

> ⚠️ **Dacă o firmă are un dosar activ de insolvență, riscul de a nu-ți fi plătite facturile este foarte mare.** Verifică întotdeauna acest tab înainte de a semna un contract.

---

#### Tab: Litigii

Dosarele din **Portal Just** (instanțele de judecată):

| Câmp | Descriere |
|---|---|
| **Nr. Dosar** | Numărul dosarului la instanță |
| **Instanța** | Tribunalul / Judecătoria |
| **Obiect** | Subiectul litigiului |
| **Materie** | Civil / Penal / Comercial / Administrativ |
| **Rol firmă** | Reclamant sau Pârât |
| **Stadiu** | Judecată / Fond / Apel / Recurs |
| **Următor termen** | Data viitorului termen de judecată |

---

#### Tab: Contracte SEAP

Contractele publice câștigate de firmă prin licitații publice:

| Câmp | Descriere |
|---|---|
| **Nr. Contract** | Identificatorul SEAP |
| **Autoritate contractantă** | Instituția publică care a plătit |
| **Titlu** | Obiectul contractului |
| **Valoare** | Suma contractului în RON |
| **Data atribuirii** | Când a fost semnat contractul |
| **Cod CPV** | Tipul de serviciu/produs |

> **Sfat:** Dacă o firmă câștigă adesea contracte publice mari, este un indicator de soliditate și reputație.

---

#### Tab: Datorii

Datoriile înregistrate la **AEGRM (Arhiva Electronică de Garanții Reale Mobiliare)**:

- Gajuri și ipoteci înregistrate
- Creditori (bănci, furnizori, stat)
- Sumele datorate

---

#### Tab: Mărci

Mărcile comerciale înregistrate la **OSIM**:

- Denumirea mărcii
- Numărul de înregistrare
- Statusul (valabilă / expirată)
- Clasele NISA (tipul produselor/serviciilor protejate)
- Data expirării

---

#### Tab: Proiecte UE

Proiectele cu finanțare europeană din **MySMIS**:

- Titlul proiectului
- Valoarea totală și finanțarea UE
- Statusul (în derulare / finalizat)

---

#### Tab: Risc

**Scorul de risc detaliat** — vezi secțiunea 7 pentru explicații complete.

Afișează:
- Scorul total (0–100) și categoria (A–E)
- Scorul fiecărei componente (financiar, juridic, fiscal, comportamental)
- **Factori de risc** identificați (ex: datorii fiscale, litigii active)
- Evoluția scorului față de calculul anterior (tendință: ↑ IMPROVING / → STABLE / ↓ DEGRADING)
- Limita de credit recomandată (estimare)

---

#### Tab: ESG

**Scorul de sustenabilitate** — vezi secțiunea 11 pentru explicații.

---

## 7. Scorul de risc — ce înseamnă A, B, C, D, E?

Scorul de risc este calculat automat pe baza mai multor surse de date și are 4 componente:

| Componentă | Pondere | Ce analizează |
|---|---|---|
| **Financiar** | 30% | Bilanțuri, lichiditate, solvabilitate (Altman Z-Score adaptat) |
| **Juridic** | 25% | Dosare la instanțe, insolvență |
| **Fiscal** | 25% | Datorii la ANAF, statut TVA, inactivitate fiscală |
| **Comportamental** | 20% | Schimbări frecvente de administratori, adrese, capital |

### Categorii de risc

| Rating | Scor | Semaforizare | Interpretare |
|---|---|---|---|
| **A** | 80–100 | 🟢 Verde | **Risc minim** — firmă solidă, indicatori excelenți |
| **B** | 60–79 | 🟡 Galben-verde | **Risc scăzut** — câteva aspecte de monitorizat |
| **C** | 40–59 | 🟠 Galben | **Risc mediu** — necesită atenție, verifică detaliile |
| **D** | 20–39 | 🔴 Portocaliu | **Risc ridicat** — prudență maximă, contracte cu garanții |
| **E** | 0–19 | ⛔ Roșu | **Risc critic** — evitați sau cereți garanții semnificative |

### Factori care scad scorul

Platforma identifică și explică fiecare factor negativ:

| Cod factor | Semnificație |
|---|---|
| `FINANCIAL_WEAK` | Indicatori financiari slabi (pierderi, lichiditate redusă) |
| `LEGAL_ISSUES` | Probleme juridice active (litigii, insolvență) |
| `FISCAL_DEBT` | Datorii fiscale semnificative la ANAF |
| `BEHAVIORAL_RISK` | Schimbări frecvente neobișnuite (administratori, sediu) |
| `INSOLVENCY_FLAG` | Procedură de insolvență activă — semnalul cel mai grav |
| `ZSCORE_DISTRESS` | Scorul Altman Z indică pericol financiar iminent |

### Limita de credit recomandată

Platforma estimează și o **limită de credit sugerată** (suma maximă pe care poți să o extinzi ca expunere față de această firmă), calculată ca procent din cifra de afaceri:

| Rating | Credit recomandat |
|---|---|
| A | Până la 25% din CA anuală |
| B | Până la 15% din CA anuală |
| C | Până la 8% din CA anuală |
| D | Până la 3% din CA anuală |
| E | Nu se recomandă credit |

> ⚠️ **Important:** Scorul este calculat algoritmic pe baza datelor publice disponibile și are caracter **informativ**. Nu înlocuiește consultanța juridică sau financiară profesională.

---

## 8. Portofolii — cum monitorizez mai multe firme

Un **portofoliu** este o listă de firme pe care le urmărești activ. Poți crea mai multe portofolii tematice: „Clienți activi", „Furnizori cheie", „Competitori", etc.

### Cum creez un portofoliu?

1. Apasă pe **„Portofolii"** în meniu (stânga)
2. Apasă butonul **„+ Portofoliu Nou"**
3. Introdu:
   - **Nume** — ex: „Furnizori IT"
   - **Descriere** — opțional
4. Apasă **„Creează"**

### Cum adaug o firmă în portofoliu?

**Metoda 1** — Din profilul firmei:
1. Deschide profilul firmei dorite
2. Apasă butonul **„+ Portofoliu"**
3. Selectează portofoliul din lista derulantă
4. Gata!

**Metoda 2** — Din rezultatele căutării:
1. Bifează una sau mai multe firme din rezultate
2. Apasă **„Adaugă la portofoliu"**
3. Selectează portofoliul

### Ce văd în portofoliu?

- Lista firmelor cu: denumire, CUI, rating risc, ultimul scor
- **Distribuția riscului** pe tot portofoliul (câte A, B, C, D, E)
- **Alerte active** pentru firmele din portofoliu
- Evoluția financiară agregată

### Cum elimin o firmă din portofoliu?

Deschide portofoliul → găsește firma → apasă butonul **„Elimină"** (iconița coș de gunoi).

---

## 9. Alerte — cum primesc notificări automate

Sistemul de alerte îți trimite notificări automate când se întâmplă ceva important la firmele pe care le monitorizezi.

### Ce tipuri de alerte există?

| Tip alertă | Când apare |
|---|---|
| **Risc crescut** | Scorul de risc scade cu mai mult de 10 puncte |
| **Insolvență nouă** | S-a deschis o procedură de insolvență |
| **Inactivitate fiscală** | ANAF a marcat firma ca inactivă |
| **Litigiu nou** | A apărut un dosar nou la instanță |
| **Schimbare administrator** | S-a schimbat administratorul sau asociatul |
| **Datorii noi** | A apărut o înscriere nouă în AEGRM |
| **Contract SEAP câștigat** | Firma a câștigat un contract public |
| **Mentiune Monitor Oficial** | Apariție nouă în Monitorul Oficial |

### Unde văd alertele?

- **Badge-ul roșu** cu număr în meniul din stânga (lângă „Alerte")
- **Notificări pop-up** în colțul din dreapta sus (în timp real, WebSocket)
- Pagina **„Alerte"** din meniu — lista completă

### Cum marchez o alertă ca citită?

- Click pe alertă → se deschide detaliile → se marchează automat ca citită
- Sau apasă **„Marchează toate citite"** pentru a le rezolva pe toate deodată

### Configurarea alertelor

1. Mergi la **Alerte** → apasă **„Configurare"**
2. Alege tipurile de alerte care te interesează
3. Configurează pragurile (ex: să primești alertă doar la risc D sau E)
4. Alege canalul: **In-app**, **Email**, **SMS**
5. Apasă **„Salvează"**

---

## 10. Rapoarte — cum generez și descarc un raport

### Tipuri de rapoarte disponibile

| Raport | Ce conține | Format |
|---|---|---|
| **Profil complet** | Toate datele despre companie | PDF, XLSX |
| **Financiar** | Evoluție bilanțuri pe ultimii ani, grafice | PDF, XLSX |
| **Due Diligence** | Analiză completă pentru parteneriat/investiție | PDF |
| **Risc** | Scoring detaliat cu factori și recomandări | PDF |
| **ESG** | Raport sustenabilitate | PDF |
| **Portofoliu** | Sumar pentru un întreg portofoliu | PDF, XLSX |

### Cum generez un raport?

1. Mergi la **„Rapoarte"** în meniu
2. Apasă **„+ Raport Nou"**
3. Caută și selectează firma (după CUI sau denumire)
4. Alege **tipul** raportului
5. Alege **formatul**: PDF / Excel (XLSX) / CSV / JSON / HTML
6. Apasă **„Generează"**

Raportul se procesează în fundal (poate dura 10–60 secunde). Primești o **notificare** când e gata.

### Cum descarc raportul?

1. Mergi la **„Rapoarte"** → secțiunea **„Rapoarte generate"**
2. Găsește raportul dorit (au dată, firmă și format)
3. Apasă butonul **„Descarcă"** (iconița ↓)

> **Notă:** Rapoartele sunt disponibile timp de **7 zile** de la generare, după care sunt șterse automat din sistem.

### Formate disponibile și când să le folosești

| Format | Când să-l alegi |
|---|---|
| **PDF** | Trimis unui partener, bancă sau avocați — arată profesional |
| **Excel (XLSX)** | Când vrei să lucrezi cu datele în propriul tabel |
| **CSV** | Importat în alt software (contabilitate, ERP) |
| **JSON** | Integrare programatică cu alte sisteme |
| **HTML** | Vizualizare în browser, ușor de trimis prin email |

---

## 11. ESG — ce înseamnă și cum îl citesc

**ESG** = Environmental (Mediu), Social, Governance (Guvernanță) — un sistem internațional de evaluare a **sustenabilității** și **responsabilității** firmelor.

### De ce contează?

Băncile și investitorii folosesc tot mai mult scorurile ESG pentru decizii de finanțare. O firmă cu scor ESG bun poate accesa finanțare mai ieftină și parteneriate europene mai ușor.

### Cele 3 categorii

| Categorie | Ce evaluează | Pondere |
|---|---|---|
| **E — Mediu** | Emisii CO₂ estimate, amenzi de mediu, aderență EU Taxonomy | 35% |
| **S — Social** | Număr angajați, contracte publice (impact comunitar), litigii de muncă | 30% |
| **G — Guvernanță** | Transparență proprietate, stabilitate administrare, conflict de interese | 35% |

### Clasificarea SFDR (regulament european)

| Clasă | Scor ESG | Semnificație |
|---|---|---|
| **Article 9+** | 85–100 | Produs cu impact sustenabil profund |
| **Article 9** | 75–84 | Obiectiv explicit de durabilitate |
| **Article 8+** | 60–74 | Promovează activ caracteristici ESG |
| **Article 8** | 50–59 | Promovează unele caracteristici ESG |
| **Article 6+** | 35–49 | Pre-ESG, indicatori parțiali pozitivi |
| **Article 6** | 0–34 | Nu promovează ESG |

### Limitări importante

> ⚠️ Scorul ESG este calculat pe baza **datelor publice disponibile** — nu toți indicatorii pot fi măsurați direct. Platforma folosește estimări (ex: amprenta de carbon estimată pe baza cifrei de afaceri și a sectorului CAEN). Scorul are caracter **informativ**, nu certificativ.

---

## 12. Fraud Graph — detectarea legăturilor suspecte

**Fraud Graph** este un modul vizual care arată **rețelele de relații** dintre companii și persoane și detectează **structuri suspecte**.

### Ce detectează?

| Tipul de risc | Descriere |
|---|---|
| **Ownership circular** | Firma A deține Firma B, care deține Firma A — structură sugestivă pentru evaziune fiscală |
| **Administratori multipli** | Aceeași persoană administrează 5+ firme simultan — uneori semnificativ |
| **Clustere de adresă** | Zeci de firme la același sediu (adresă de firmă de tip „casă de adresă") |
| **Firme phoenix** | O firmă intră în insolvență, și imediat apare una nouă cu aceiași administratori |

### Cum vizualizez graful?

1. Mergi la **„Fraud Graph"** în meniu
2. Caută firma care te interesează (după CUI)
3. Graful se deschide interactiv:
   - **Noduri albastre** = Companii
   - **Noduri mov** (rotunde) = Persoane fizice
   - **Linii colorate** = Relații (administrare, asociere, proprietate)
   - **Linii animate** = Conexiuni marcate ca suspecte

### Cum interacționez cu graful?

| Acțiune | Cum |
|---|---|
| **Zoom in/out** | Rotița mouse-ului |
| **Deplasare** | Click + drag pe fundal |
| **Detalii nod** | Click pe un nod (companie sau persoană) |
| **Orientare** | MiniMap în colțul din dreapta jos |

### Fraud Score

Fiecare analiză generează un **fraud score** (0–100):
- **0–30** — Risc de fraudă scăzut
- **31–60** — Risc moderat, necesită investigare
- **61–100** — Risc ridicat — structuri suspecte detectate

> ⚠️ **Disclaimer important:** Alertele de fraudă sunt generate **algoritmic** pe baza structurii relațiilor și a tiparelor statistice. Ele constituie **suspiciuni**, nu acuzații legale. O conexiune detectată nu înseamnă neapărat fraudă — poate fi o structură corporativă legitimă.

---

## 13. SEAP — licitații publice

**SEAP** (Sistemul Electronic de Achiziții Publice) este baza de date cu toate licitațiile și contractele publice din România.

### Ce găsesc în secțiunea SEAP?

#### Tab: Licitații Active
Proceduri de achiziție publică **deschise** (mai poți depune ofertă):
- Titlul licitației
- Autoritatea contractantă (primărie, minister, spital, etc.)
- Valoarea estimată
- **Termenul limită de depunere** — important!
- Tipo procedură (cerere de ofertă, licitație deschisă, negociere)

#### Tab: Contracte Atribuite
Contracte publice deja câștigate:
- Cine a câștigat și cu ce sumă
- Autoritatea contractantă
- Data atribuirii

#### Tab: Statistici
- Valoarea totală a contractelor pe an
- Top autorități contractante
- Distribuție pe tipuri de proceduri

### Cum filtrez licitațiile?

- **Cod CPV** — tipul de bunuri/servicii (ex: 72000000 = IT)
- **Valoare minimă** — filtrezi contractele mari
- **Termen de depunere** — afișezi doar cele la care mai ai timp
- **Autoritate contractantă** — o anumită instituție publică

---

## 14. Firme Noi

Secțiunea **„Firme Noi"** afișează companiile înregistrate **recent la ONRC** — o sursă excelentă de prospecți noi.

### Ce găsesc?

- Lista firmelor înregistrate în ultima săptămână / lună
- Filtru pe județ, cod CAEN, formă juridică
- Grafic de tendință: câte firme noi pe zi

### Cum le folosesc?

- Dacă vinzi un produs/serviciu pentru firme noi (contabilitate, IT, mobilier birou), există clienți potențiali chiar acolo
- Poți adăuga direct în portofoliu pentru monitorizare

---

## 15. RedBill — datorii restante

**RedBill** este modulul pentru evaluarea **comportamentului de plată** al firmelor.

### Ce găsesc?

- **Scorul de plată** al unei firme (A–E)
- **Datoriile restante** declarate
- **Istoricul de plăți** față de furnizori
- **Top datornici** — firmele cu cele mai mari restanțe

### Cum verific o firmă?

1. Mergi la **„RedBill"** în meniu
2. Introdu **CUI-ul** firmei în câmpul de căutare
3. Apasă **„Verifică"**

### Ce înseamnă scorul de plată?

| Rating | Comportament |
|---|---|
| **A** | Plătitor exemplar — plătește la termen sau mai devreme |
| **B** | Plătitor bun — max 15 zile întârziere ocazional |
| **C** | Plătitor moderat — întârzieri frecvente 15–30 zile |
| **D** | Plătitor problematic — întârzieri > 30 zile |
| **E** | Plătitor rău — datorii restante semnificative |

---

## 16. Asistentul AI

Platforma include un **asistent inteligent** bazat pe Anthropic Claude care răspunde la întrebări despre firme în **limbaj natural**.

### Cum îl folosesc?

1. Apasă pe **„AI Agent"** în meniu
2. Scrie întrebarea ta în câmpul de chat
3. Apasă Enter sau butonul „Trimite"

### Exemple de întrebări

```
"Care este scorul de risc al firmei cu CUI 14399840?"

"Câte contracte publice a câștigat Rompetrol în 2025?"

"Compară riscul firmei ABC SRL cu DEF SA"

"Ce firme active din județul Cluj au cod CAEN 6201 și rating A?"

"Ce s-a schimbat la firma XYZ în ultimele 30 de zile?"
```

### Limitări

- Asistentul cunoaște doar datele existente **în baza de date a platformei**
- Nu accesează internet în timp real
- Răspunsurile sunt bazate pe date publice — nu constituie consultanță juridică
- Pot exista erori — verifică întotdeauna datele importante direct pe sursă

---

## 17. Setări și profil personal

### Cum îmi schimb parola?

1. Apasă pe **avatarul/numele tău** din colțul din dreapta sus (sau din jos în sidebar)
2. Selectează **„Profil"** sau **„Setări"**
3. Accesează secțiunea **„Schimbare parolă"**
4. Introdu parola veche și noua parolă (minim 8 caractere)
5. Apasă **„Salvează"**

### Setări notificări

În **Setări → Notificări** poți configura:
- Canalele preferate (in-app, email, SMS)
- Frecvența emailurilor (imediat / zilnic rezumat / săptămânal)
- Tipurile de alerte pe care vrei să le primești

### Informații cont

- **Email** — nu poate fi schimbat (contact adm)
- **Organizație** — afișată, gestionată de administrator
- **Rol** — viewer / analyst / admin (atribuit de administrator)

---

## 18. Trucuri și scurtături utile

| Scurtătură / Truc | Ce face |
|---|---|
| **`Ctrl + K`** | Deschide căutarea rapidă de oriunde |
| **Click pe rating-ul colorat** | Deschide detaliile scorului de risc |
| **Bifează mai multe firme** din căutare | Adaugă toate simultan în portofoliu |
| **Tab: Financiar → grafic** | Hover pe punctele graficului pentru detalii pe an |
| **Fraud Graph → click nod** | Afișează toate relațiile aferente persoanei/firmei |
| **Alerte → sort după urgență** | Click pe coloana „Prioritate" pentru a sorta |
| **Raport PDF → descarcă direct** | Dacă fișierul e gata, linkul de descărcare apare imediat |
| **Dashboard → click pe o categorie Pie Chart** | Filtrează automat căutarea pe acea categorie de risc |

---

## 19. Întrebări frecvente (FAQ)

**Q: De unde vin datele?**  
A: Din surse publice oficiale: ANAF, ONRC, BPI, Portal Just, AEGRM, OSIM, SEAP, BNR, INS, Monitor Oficial, MySMIS. Datele sunt sincronizate automat zilnic/săptămânal.

---

**Q: Cât de actualizate sunt datele?**  
A: Depinde de sursa publică:
- **ANAF, BPI, SEAP, BNR** — actualizate zilnic
- **ONRC (Registrul Comerțului)** — la momentul interogării, cache 30 zile
- **AEGRM, OSIM** — actualizate săptămânal
- **Bilanțuri** — depind de momentul depunerii la ANAF (anual, cu întârziere 0–9 luni față de data bilanțului)

---

**Q: Scorul de risc este 100% corect?**  
A: Scorul este calculat algoritmic pe baza datelor publice disponibile și are caracter **estimativ**. Poate fi afectat de date publice incomplete sau cu întârziere. Nu înlocuiește o analiză financiară completă sau consultanța unui expert.

---

**Q: Pot vedea datele despre orice firmă din România?**  
A: Da, platforma acoperă toate firmele înregistrate la ONRC — milioane de entități. Datele afișate sunt **informații publice** la care orice cetățean are drept de acces.

---

**Q: Datele mele personale sunt în siguranță?**  
A: Da. Platforma respectă GDPR:
- CNP-urile sunt **hashed** (criptate) — nu sunt stocate în clar
- Sesiunile sunt protejate cu JWT RS256
- Toate conexiunile sunt criptate HTTPS/TLS

---

**Q: Nu găsesc o firmă — de ce?**  
A: Posibil că:
1. CUI-ul introdus nu este corect (verifică dacă lipsesc sau sunt în plus cifre)
2. Firma este foarte nouă (înregistrată în ultimele 24–48 ore — sincronizarea nu a ajuns la ea)
3. Firma nu există în baza de date ONRC
Încearcă și cu denumirea completă sau parțială.

---

**Q: Pot exporta date în bulk pentru mai multe firme?**  
A: Da, prin endpoint-ul batch `/api/v1/companies/batch` (dacă ai acces tehnic la API). Din interfața grafică, poți genera rapoarte de portofoliu pentru un set de firme.

---

**Q: Aplicația funcționează pe mobil?**  
A: Interfața este responsive și funcționează pe tablete și telefoane mobile, dar este **optimizată pentru desktop** (rezoluție minimă recomandată 1280px × 720px). Unele funcționalități (Fraud Graph vizual) sunt mai ușor de folosit pe ecran mare.

---

**Q: Cum pot raporta o eroare sau solicita o funcționalitate nouă?**  
A: Contactează echipa tehnică prin email sau prin formularul de suport din aplicație (secțiunea **„Ajutor"** sau **„Contact"**).

---

## 20. Glosar de termeni

| Termen | Definiție |
|---|---|
| **CUI** | Cod Unic de Identificare — numărul fiscal al firmei (ex: 14399840 sau RO14399840 pentru plătitori TVA) |
| **ONRC** | Oficiul Național al Registrului Comerțului — instituția unde se înregistrează firmele |
| **ANAF** | Agenția Națională de Administrare Fiscală — colectează taxele și publică bilanțuri |
| **BPI** | Buletinul Procedurilor de Insolvență — publicația oficială a dosarelor de insolvență |
| **AEGRM / RNPM** | Arhiva Electronică de Garanții Reale Mobiliare — gajuri și datorii înscrise |
| **OSIM** | Oficiul de Stat pentru Invenții și Mărci — mărci și brevete |
| **SEAP / SICAP** | Sistemul Electronic de Achiziții Publice — licitații și contracte publice |
| **BNR** | Banca Națională a României — cursuri valutare |
| **INS** | Institutul Național de Statistică — date macroeconomice |
| **CAEN** | Clasificarea Activităților din Economia Națională — codul activității principale a firmei |
| **TVA** | Taxa pe Valoarea Adăugată |
| **Split TVA** | Regim special de plată TVA în cont separat (pentru firmele cu probleme fiscale) |
| **Inactiv fiscal** | ANAF a suspendat dreptul firmei de a emite facturi |
| **Insolvență** | Procedura legală prin care o firmă care nu-și poate plăti datoriile intră sub supravegherea unui tribunal |
| **Reorganizare** | Prima etapă a insolvenței — firma încearcă să se redreseze |
| **Faliment** | Etapa finală a insolvenței — firma se lichidează |
| **Altman Z-Score** | Formula matematică originară din 1968 care prezice riscul de faliment pe baza indicatorilor financiari, adaptată de platformă pentru specificul românesc |
| **ESG** | Environmental, Social, Governance — set de criterii de evaluare a sustenabilității |
| **CSRD** | Corporate Sustainability Reporting Directive — directiva UE care impune raportare ESG pentru firmele mari |
| **SFDR** | Sustainable Finance Disclosure Regulation — regulament EU care clasifică produsele financiare pe categorii ESG |
| **Due Diligence** | Investigație detaliată înainte de o tranzacție, investiție sau parteneriat |
| **Neo4j** | Baza de date orientată pe grafuri folosită pentru analiza relațiilor dintre companii și persoane |
| **JWT** | JSON Web Token — formatul tokenului de autentificare |
| **WebSocket** | Protocol de comunicare bidirecțional pentru notificări în timp real |
| **MinIO** | Sistem de stocare compatibil Amazon S3 folosit pentru rapoartele generate |
| **Celery** | Sistem de procesare a task-urilor în fundal (sincronizări, rapoarte, calcule) |

---

*RomBiz Intelligence Platform — Date colectate din surse publice oficiale. Scorurile și analizele au caracter informativ și nu constituie consultanță juridică sau financiară. Ultima actualizare: Martie 2026.*
