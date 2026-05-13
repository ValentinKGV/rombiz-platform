# RomBiz Intelligence — Ghid de Utilizare

> **Versiune:** 1.0  
> **Ultima actualizare:** Ianuarie 2025  
> **Platformă:** RomBiz Intelligence — Business Intelligence pentru firmele din România

---

## Cuprins

1. [Introducere](#1-introducere)
2. [Cerințe de sistem](#2-cerințe-de-sistem)
3. [Autentificare și Înregistrare](#3-autentificare-și-înregistrare)
4. [Dashboard — Pagina principală](#4-dashboard--pagina-principală)
5. [Căutare Firme](#5-căutare-firme)
6. [Profil Companie](#6-profil-companie)
7. [Portofolii de Monitorizare](#7-portofolii-de-monitorizare)
8. [Sistem de Alerte](#8-sistem-de-alerte)
9. [SEAP — Licitații Publice](#9-seap--licitații-publice)
10. [Firme Noi](#10-firme-noi)
11. [Fraud Graph — Detecția Fraudelor](#11-fraud-graph--detecția-fraudelor)
12. [ESG Dashboard](#12-esg-dashboard)
13. [RedBill — Facturi Restante](#13-redbill--facturi-restante)
14. [Rapoarte și Export](#14-rapoarte-și-export)
15. [AI Agent — Asistent Inteligent](#15-ai-agent--asistent-inteligent)
16. [Analiză Predictivă](#16-analiză-predictivă)
17. [Relații între Companii](#17-relații-între-companii)
18. [Due Diligence](#18-due-diligence)
19. [Market Intelligence](#19-market-intelligence)
20. [Supply Chain — Lanț de Aprovizionare](#20-supply-chain--lanț-de-aprovizionare)
21. [Document Intelligence](#21-document-intelligence)
22. [Conformitate Regulamentară](#22-conformitate-regulamentară)
23. [Analiză Geospațială](#23-analiză-geospațială)
24. [API Marketplace](#24-api-marketplace)
25. [Optimizare Portofoliu](#25-optimizare-portofoliu)
26. [Expansiune Internațională](#26-expansiune-internațională)
27. [Blockchain Audit Trail](#27-blockchain-audit-trail)
28. [Administrare (Admin)](#28-administrare-admin)
29. [Shortcuturi și Sfaturi](#29-shortcuturi-și-sfaturi)
30. [FAQ — Întrebări Frecvente](#30-faq--întrebări-frecvente)

---

## 1. Introducere

**RomBiz Intelligence** este o platformă completă de Business Intelligence dedicată firmelor din România. Platforma agregă date din peste 12 surse publice oficiale (ANAF, ONRC, BPI, SEAP, PortalJust, BNR, AEGRM, OSIM, Monitor Oficial, BVB, ASF, INS) și oferă:

- **Căutare avansată** în baza de date a tuturor companiilor din România
- **Scoring de risc** automat cu 5 categorii (A–E)
- **Scoring ESG** (Environmental, Social, Governance)
- **Detectarea fraudelor** prin analiza grafurilor de relații
- **Monitoring în timp real** prin alerte configurabile
- **Rapoarte profesionale** exportabile în PDF, Excel, CSV
- **Asistent AI** pentru interogări în limbaj natural
- **Analiză predictivă** a riscului de insolvență
- **Audit trail blockchain** pentru trasabilitate completă

---

## 2. Cerințe de Sistem

### Browser-e suportate
| Browser | Versiune minimă |
|---------|----------------|
| Google Chrome | 90+ |
| Mozilla Firefox | 88+ |
| Microsoft Edge | 90+ |
| Safari | 14+ |

### Cerințe
- Conexiune la internet stabilă
- Rezoluție ecran minimă: 1280×720 (recomandat: 1920×1080)
- JavaScript activat în browser

---

## 3. Autentificare și Înregistrare

### 3.1 Prima accesare

1. Deschideți browser-ul și navigați la adresa platformei
2. Veți fi redirecționat automat la pagina de **Login**

### 3.2 Înregistrarea unui cont nou

1. Pe pagina de login, apăsați **„Creează cont"** (link în partea de jos)
2. Completați formularul de înregistrare:
   - **Email** — adresa de email corporativă
   - **Parolă** — minim 8 caractere
   - **Prenume** și **Nume**
   - **Numele organizației** — firma dvs.
3. Apăsați **„Înregistrare"**
4. Contul va fi creat și puteți reveni la pagina de login

### 3.3 Autentificarea (Login)

1. Introduceți **Email-ul** și **Parola**
2. Apăsați butonul **„Intră în Univers"**
3. După autentificarea reușită, veți fi redirecționat la **Dashboard**

### 3.4 Deconectarea (Logout)

- Apăsați butonul **Logout** (iconița 🚪) din sidebar-ul din stânga, în partea de jos
- Veți fi redirecționat automat la pagina de login

### 3.5 Sesiuni și Securitate

- Token-ul de acces este salvat automat în browser
- Sesiunea expiră automat după perioada configurată de administrator
- La expirare, sistemul va reîmprospăta token-ul automat (refresh token)
- Dacă refresh-ul eșuează, veți fi redirecționat la login

---

## 4. Dashboard — Pagina Principală

După autentificare, pagina principală afișează un **overview** complet al datelor:

### 4.1 Indicatori Cheie (KPIs)

- **Total Companii** — numărul total de firme monitorizate
- **Companii Active** — firme cu statut ACTIV
- **Companii cu Datorii** — firme cu datorii (AEGRM)
- **Firme Insolvente** — firme în procedură de insolvență

### 4.2 Distribuția Riscului

Grafic de tip **Pie Chart** care arată distribuția companiilor pe categorii de risc:
- **A** (Verde) — Risc minim
- **B** (Galben-verde) — Risc scăzut
- **C** (Galben) — Risc mediu
- **D** (Portocaliu) — Risc ridicat
- **E** (Roșu) — Risc critic

### 4.3 Top Sectoare

Grafic **Bar Chart** cu cele mai populare sectoare de activitate (coduri CAEN).

### 4.4 Alerte Recente

Lista ultimelor alerte generate (maxim 5), cu link rapid la detalii.

### 4.5 Widget-uri Suplimentare

- **ESG Overview** — distribuția SFDR prin categorii
- **Status conexiune WebSocket** — indicator live (verde = conectat)

### 4.6 Notificări în Timp Real

Platforma folosește **WebSocket** pentru a vă notifica instant la:
- Alerte noi de risc
- Schimbări de stare la firmele monitorizate
- Rapoarte finalizate

Notificările apar ca toast-uri în colțul din dreapta sus.

---

## 5. Căutare Firme

**Ruta:** `/search` | **Meniu:** Căutare

### 5.1 Căutare Rapidă

1. Navigați la secțiunea **Căutare** din sidebar
2. Introduceți în câmpul de căutare:
   - **Denumirea firmei** (parțial sau complet)
   - **CUI** (Cod Unic de Identificare)
   - **Nr. Registrul Comerțului** (J40/1234/2020)
3. Apăsați **Enter** sau butonul de căutare
4. Rezultatele apar imediat sub formă de tabel

### 5.2 Filtre Avansate

Apăsați **„Filtre avansate"** pentru a rafina rezultatele:

| Filtru | Descriere |
|--------|-----------|
| Județ | Filtrare pe județ (dropdown) |
| Cod CAEN | Activitate principală |
| Stare | ACTIVA, INACTIVA, RADIATA |
| Rating risc | A, B, C, D, E |
| Capital social | Interval min–max |
| Anul înființării | Interval |
| Plătitor TVA | Da / Nu |

### 5.3 Rezultate

Fiecare rezultat afișează:
- **Denumire** (link spre profil)
- **CUI**
- **Județ**
- **Cod CAEN**
- **Stare**
- **Rating Risc** (badge colorat)
- **Data Quality Score** (0–100%)

### 5.4 Shortcut: `Ctrl+K`

Apăsați **Ctrl+K** de oriunde în aplicație pentru a deschide rapid pagina de căutare.

---

## 6. Profil Companie

**Ruta:** `/company/:cui`

Accesați profilul unei companii apăsând pe denumirea ei din rezultatele căutării.

### 6.1 Informații Generale

- Denumire, CUI, Nr. Registrul Comerțului
- Forma juridică (SRL, SA, PFA, etc.)
- Stare (ACTIVA / INACTIVA / RADIATA)
- Data înființării / Data radierii
- Cod CAEN principal + descriere
- Capital social
- Adresă completă, județ, localitate

### 6.2 Status Fiscal (ANAF)

- Plătitor TVA (Da/Nu)
- TVA la încasare
- Split TVA
- Inactiv fiscal

### 6.3 Tab-uri Disponibile

Profilul companiei are mai multe tab-uri:

| Tab | Conținut |
|-----|---------|
| **Financiar** | Date financiare pe ani: cifra de afaceri, profit net, nr. angajați, datorii totale. Grafice de evoluție |
| **Persoane** | Administratori, asociați, directori cu funcție, CNP parțial, cotă de participare |
| **Insolvență** | Dosare BPI, status, practician, tribunal |
| **Litigii** | Dosare din Portal Just, materie, stadiu |
| **Contracte SEAP** | Contracte publice, valoare, autoritate contractantă |
| **Datorii** | Datorii la bugetul de stat (AEGRM), sume, date |
| **Mărci** | Mărci înregistrate la OSIM |
| **Proiecte UE** | Proiecte finanțate cu fonduri europene |
| **Risc** | Scor de risc detaliat, rating, factori |
| **ESG** | Scor ESG, categorii Environment/Social/Governance |

### 6.4 Acțiuni Rapide

- **Adaugă în portofoliu** — salvează firma într-un portofoliu de monitorizare
- **Generează raport** — creează un raport PDF/Excel
- **Setează alertă** — configurează notificări pentru modificări

---

## 7. Portofolii de Monitorizare

**Ruta:** `/portfolios` | **Meniu:** Portofolii

### 7.1 Ce este un Portofoliu?

Un portofoliu este o colecție de companii pe care le monitorizați activ. Puteți crea portofolii tematice (ex: „Clienți", „Furnizori", „Competiție").

### 7.2 Crearea unui Portofoliu

1. Navigați la **Portofolii**
2. Apăsați **„Portofoliu Nou"**
3. Completați:
   - **Nume** — ex: „Furnizori IT"
   - **Descriere** (opțional)
4. Apăsați **„Creează"**

### 7.3 Adăugarea Companiilor

- Din profilul unei companii: apăsați **„Adaugă în portofoliu"** și selectați portofoliul
- Din lista de căutare: selectați companiile dorite și apăsați **„Adaugă la..."**

### 7.4 Monitorizare

Portofoliul afișează:
- Lista companiilor cu indicatori cheie
- Distribuția riscului pe portofoliu
- Evoluția financiară agregată
- Alerte active pentru firmele din portofoliu

---

## 8. Sistem de Alerte

**Ruta:** `/alerts` | **Meniu:** Alerte

### 8.1 Tipuri de Alerte

| Tip | Declanșare |
|-----|-----------|
| **Risc crescut** | Scorul de risc crește semnificativ |
| **Insolvență** | Apare o procedură de insolvență |
| **Modificare ONRC** | Se schimbă administrator, sediu, obiect de activitate |
| **Datorii noi** | Apar datorii la AEGRM |
| **Contract SEAP** | Firma câștigă un contract public |
| **Inactivitate fiscală** | ANAF marchează firma ca inactivă |
| **Litigiu nou** | Apare un dosar nou pe Portal Just |

### 8.2 Vizualizarea Alertelor

- **Alerte necitite** afișate cu badge în sidebar (număr)
- Lista alertelor cu: tip, titlu, companie, data, prioritate
- Apăsați pe o alertă pentru detalii complete

### 8.3 Canale de Notificare

- **In-app** — notificări toast în browser (implicit)
- **Email** — se configurează în profil
- **SMS** — disponibil la cerere (necesită Twilio)
- **WebSocket** — notificări push în timp real

### 8.4 Configurarea Alertelor

1. Navigați la **Alerte**
2. Apăsați **„Configurare alerte"**
3. Selectați tipurile de alerte dorite
4. Setați pragul de notificare (ex: doar risc D și E)
5. Alegeți canalele preferate
6. Apăsați **„Salvează"**

---

## 9. SEAP — Licitații Publice

**Ruta:** `/seap` | **Meniu:** SEAP

### 9.1 Prezentare

Modulul SEAP afișează licitațiile publice din România. Datele sunt sincronizate din Sistemul Electronic de Achiziții Publice.

### 9.2 Tab-uri SEAP

| Tab | Descriere |
|-----|-----------|
| **Licitații Active** | Proceduri de achiziție deschise, cu termen de depunere |
| **Contracte Atribuite** | Contracte câștigate, cu valoare și câștigător |
| **Statistici** | Grafice: valoare totală pe an, top autorități contractante |

### 9.3 Informații Afișate

- Număr anunț / ID procedură
- Titlu licitație
- Autoritate contractantă
- Tip procedură (cerere ofertă, licitație deschisă, etc.)
- Valoare estimată și monedă
- Termen limită de depunere
- Link către SEAP

### 9.4 Filtrare

- După autoritate contractantă
- După cod CPV (obiect achiziție)
- După valoare (interval)
- După termenul de depunere

---

## 10. Firme Noi

**Ruta:** `/new-companies` | **Meniu:** Firme Noi

Afișează companiile înregistrate recent la ONRC:

- Lista firmelor noi pe ultima săptămână/lună
- Filtru pe județ, CAEN, formă juridică
- Grafice de tendințe: câte firme noi pe zi/săptămână
- Posibilitate de a adăuga direct în portofoliu

---

## 11. Fraud Graph — Detecția Fraudelor

**Ruta:** `/fraud` | **Meniu:** Fraud Graph

### 11.1 Cum Funcționează

Modulul de fraud graph folosește **Neo4j** (bază de date graf) pentru a analiza relațiile dintre companii și persoane. Detectează:

- **Ownership circular** — A deține B, B deține C, C deține A
- **Administratori partajați** — aceeași persoană la mai multe firme suspecte
- **Cluster de adrese** — mai multe firme la aceeași adresă
- **Rețele de risc** — firme riscante conectate prin persoane

### 11.2 Vizualizare

Graful este afișat interactiv folosind **ReactFlow**:

- **Noduri albastre** = Companii
  - Roșu = risc ridicat, Galben = risc mediu, Gri = risc scăzut
- **Noduri mov** (cerc) = Persoane fizice
- **Muchii** = relații (administrare, asociere, proprietate)
  - Animate = conexiuni suspecte

### 11.3 Interacțiune

- **Zoom** cu scroll-ul mouse-ului
- **Pan** (deplasare) ținând click
- **Click pe nod** pentru detalii
- **MiniMap** în colțul din dreapta jos pentru orientare
- **Controale** de zoom în colțul de sus

### 11.4 Scorul de Fraud

Fiecare analiză returnează un **fraud score** (0–100) cu detalii despre tipurile de risc detectate.

---

## 12. ESG Dashboard

**Ruta:** `/esg` | **Meniu:** ESG

### 12.1 Ce este ESG?

**ESG** (Environmental, Social, Governance) este un sistem de evaluare a sustenabilității companiilor.

### 12.2 Scoruri Afișate

| Categorie | Ce măsoară | Pondere |
|-----------|-----------|---------|
| **Environment** | Impact de mediu, emisii CO₂, energie regenerabilă | 30% |
| **Social** | Drepturile angajaților, diversitate, comunitate | 35% |
| **Governance** | Transparență, anti-corupție, structura de conducere | 35% |

### 12.3 Clasificare SFDR

- **Article 9** — Produs durabil
- **Article 8** — Promovează caracteristici ESG
- **Article 6** — Nu promovează ESG

### 12.4 Funcționalități

- Scor ESG detaliat pe companie
- Benchmark pe sector (comparare cu media industriei)
- Screening ESG pe portofoliu
- Alertă la câderea sub un prag ESG
- Recomandări de îmbunătățire

---

## 13. RedBill — Facturi Restante

**Ruta:** `/redbill` | **Meniu:** RedBill

### 13.1 Funcționalitate

RedBill monitorizează facturile restante și comportamentul de plată al companiilor:

- **Verificare rapidă** — introduceți CUI-ul pentru a vedea dacă are facturi restante
- **Scoring de plată** — clasificare A–E pe baza istoricului de plăți
- **Top datornici** — lista companiilor cu cele mai mari restanțe
- **Trend-uri** — evoluția restanțelor în timp

---

## 14. Rapoarte și Export

**Ruta:** `/reports` | **Meniu:** Rapoarte

### 14.1 Tipuri de Rapoarte

| Raport | Descriere |
|--------|-----------|
| **Profil complet** | Toate datele disponibile despre o companie |
| **Raport financiar** | Evoluție financiară pe ultimii ani |
| **Due diligence** | Analiză completă pentru parteneriat |
| **Risc** | Detalii scoring de risc |
| **ESG** | Raport ESG detaliat |
| **Portofoliu** | Sumar portofoliu de companii |

### 14.2 Formate de Export

- **PDF** — raport formatat profesional
- **Excel (XLSX)** — date structurate în tabele
- **CSV** — date brute pentru analize
- **JSON** — date structurate pentru integrări
- **HTML** — raport web interactiv

### 14.3 Generarea unui Raport

1. Navigați la **Rapoarte**
2. Apăsați **„Raport Nou"**
3. Selectați:
   - Compania (căutare după CUI/denumire)
   - Tipul raportului
   - Formatul dorit
4. Apăsați **„Generează"**
5. Raportul se procesează (poate dura 10–30 secunde)
6. Descărcați raportul din lista rapoartelor

### 14.4 Rapoarte Generate Anterior

Lista rapoartelor anterioare cu:
- Tip, companie, format
- Data generării
- Link de descărcare (valid 7 zile)

---

## 15. AI Agent — Asistent Inteligent

**Ruta:** `/ai` | **Meniu:** AI Agent

### 15.1 Ce Poate Face

Asistentul AI (bazat pe **Claude**) poate:
- Răspunde la întrebări despre companii specifice
- Compara firme din aceeași industrie
- Explica scorurile de risc
- Genera rezumate din date financiare
- Recomanda acțiuni bazate pe analiză

### 15.2 Cum se Folosește

1. Navigați la **AI Agent**
2. Introduceți întrebarea în limbaj natural, de exemplu:
   - *„Care este riscul pentru firma cu CUI 12345678?"*
   - *„Compară cifra de afaceri pentru Top 5 firme IT din Cluj"*
   - *„Ce firme noi SRL au fost înregistrate în București săptămâna aceasta?"*
   - *„Generează un sumar pentru portofoliul ‹Furnizori›"*
3. Apăsați **Enter** sau butonul de trimitere
4. AI-ul va analiza datele și va răspunde cu text + vizualizări (dacă e cazul)

### 15.3 Instrumente AI (Tools)

AI-ul are acces la:
- Căutare companii
- Date financiare
- Scoring de risc
- Contracte SEAP
- Date de insolvență
- Anomalii financiare

---

## 16. Analiză Predictivă

**Ruta:** `/predictive` | **Meniu:** (accesat din sidebar sau link)

### 16.1 Funcționalități

- **Predicție insolvență** — probabilitatea ca o firmă să intre în insolvență în 12 luni
- **Trend financiar** — proiecție a cifrei de afaceri și profitului
- **Anomalii** — detectarea abaterilor financiare neobișnuite
- **Clasificare sector** — comparare cu media sectorului

### 16.2 Utilizare

1. Introduceți CUI-ul companiei
2. Selectați tipul de analiză
3. Vizualizați graficul de predicție cu intervale de încredere
4. Consultați factorii principali ai scorului

---

## 17. Relații între Companii

**Ruta:** `/relationships`

Vizualizarea relațiilor dintre companii:

- **Acționariat** — cine deține pe cine
- **Management comun** — administratori partajați
- **Furnizori/Clienți** — relații comerciale (din SEAP)
- **Grup de companii** — firme aflate sub același control

Graful de relații se afișează interactiv cu posibilitate de expandare a nodurilor.

---

## 18. Due Diligence

**Ruta:** `/due-diligence`

### 18.1 Flux de Lucru

1. Introduceți CUI-ul companiei țintă
2. Platforma rulează automat verificări pe:
   - Identitate legală (ONRC)
   - Status fiscal (ANAF)
   - Insolvență (BPI)
   - Litigii (Portal Just)
   - Datorii publice (AEGRM)
   - Contracte publice (SEAP)
   - Sancțiuni (ASF)
   - Proprietate intelectuală (OSIM)
3. Se generează un **Raport Due Diligence** cu:
   - Checkbox pe fiecare verificare (OK / Atenție / Risc)
   - Scor global de due diligence
   - Recomandarea: Aprobat / Revizuire / Respins

---

## 19. Market Intelligence

**Ruta:** `/market`

### 19.1 Funcționalități

- **Analiză sectorială** — metrici pe coduri CAEN
- **Concentrare piață** (indice HHI) — cât de monopolizat este un sector
- **Top companii** per sector — cifra de afaceri, angajați, profit
- **Trend de piață** — evoluția numărului de firme și a veniturilor
- **Date macroeconomice** — PIB, inflație, șomaj (din INS)

### 19.2 Utilizare

1. Selectați codul CAEN de interes
2. Vizualizați graficele și tabelele de analiză
3. Comparați cu alte sectoare
4. Exportați datele

---

## 20. Supply Chain — Lanț de Aprovizionare

**Ruta:** `/supply-chain`

Monitorizare a lanțului de aprovizionare:

- **Mapping furnizori** — vizualizare lanț de furnizori (tiers)
- **Risk mapping** — identificarea furnizorilor cu risc
- **Concentrare** — dependența de un singur furnizor
- **Benchmark alternativ** — sugestii de furnizori alternativi
- **Alerte supply chain** — notificări la evenimente pe lanț

---

## 21. Document Intelligence

**Ruta:** `/documents`

### 21.1 Funcționalități

- **Upload** — încărcați documente (contracte, bilanțuri, acte)
- **OCR** — extracție text din scanări/imagini
- **Extracție entități** — identificare automată de: CUI, sume, date, nume
- **Clasificare** — clasificare automată a tipului de document
- **Sumarizare** — rezumat generat de AI

### 21.2 Utilizare

1. Apăsați **„Încarcă Document"**
2. Selectați fișierul (PDF, DOCX, imagine)
3. Așteptați procesarea (10–60 secunde)
4. Vizualizați rezultatele: text extras, entități, sumar

---

## 22. Conformitate Regulamentară

**Ruta:** `/compliance`

### 22.1 Verificări

- **GDPR** — conformitate cu regulamentul de protecție a datelor
- **AML/KYC** — Anti Money Laundering / Know Your Customer
- **Sancțiuni** — verificare contra listelor de sancțiuni internaționale
- **PEP** — Persoane Expuse Politic
- **Beneficiari reali** — conform Registrului Beneficiarilor Reali

### 22.2 Generare Checklist

1. Selectați compania
2. Selectați tipul de verificare
3. Platforma generează un checklist cu statusul fiecărei verificări
4. Exportați raportul de conformitate

---

## 23. Analiză Geospațială

**Ruta:** `/geo`

### 23.1 Tab-uri

| Tab | Descriere |
|-----|-----------|
| **Heatmap** | Hartă a României cu densitatea firmelor pe județ |
| **Proximitate** | Căutare firme într-o rază geografică |
| **Statistici** | Date demografice și economice pe județ |

### 23.2 Heatmap

- Hartă interactivă (Leaflet + OpenStreetMap)
- Cercuri colorate pe județ — dimensionate după numărul de companii
- Roșu = densitate mare, Albastru = densitate mică
- Click pe cerc pentru detalii județ

### 23.3 Căutare Proximitate

1. Introduceți adresa sau coordonatele
2. Setați raza de căutare (km)
3. Vedeți lista firmelor din perimetru
4. Aplicați filtre suplimentare (CAEN, risc, etc.)

---

## 24. API Marketplace

**Ruta:** `/marketplace`

### 24.1 Funcționalitate

Platforma expune un **API REST** pe care îl puteți integra în propriile sisteme.

### 24.2 Management Chei API

1. Navigați la **API Marketplace**
2. Apăsați **„Generează Cheie API"**
3. Denumiți cheia și setați permisiunile
4. **Copiați cheia** — aceasta se afișează o singură dată!
5. Folosiți cheia în header: `X-API-Key: your_key_here`

### 24.3 Rate Limits

Planul implicit permite:
- **100 cereri/minut** per cheie API
- Creștere la cerere pentru planuri premium

### 24.4 Documentație SDK

Exemple de cod disponibile pentru:
- **Python** (requests/httpx)
- **JavaScript** (fetch/axios)
- **cURL**

### 24.5 Webhook-uri

Configurați URL-uri de callback pentru a primi notificări automate:
1. Apăsați **„Adaugă Webhook"**
2. Introduceți URL-ul endpoint-ului
3. Selectați evenimentele dorite
4. Salvați — secretul de semnare va fi generat automat

---

## 25. Optimizare Portofoliu

**Ruta:** `/portfolio-opt`

- **Analiză Markowitz** — optimizare risc/return pe portofoliu
- **Risk Parity** — alocare egalizată pe risc
- **Efficient Frontier** — vizualizare grafică a frontierei eficiente
- **Simulare Monte Carlo** — scenarii probabilistice de evoluție
- **Recomandări de rebalansare** — sugestii automate de ajustare

---

## 26. Expansiune Internațională

**Ruta:** `/international`

Modul destinat companiilor care analizează parteneriate externe:

- **Verificare companii din UE** — căutare în registre europene
- **Risc de țară** — scoring pentru 180+ țări
- **Reglementări vamale** — tarife, bariere
- **Comparare jurisdicții** — taxe, reglementări
- **Partner matching** — identificare potențiali parteneri

---

## 27. Blockchain Audit Trail

**Ruta:** `/blockchain`

### 27.1 Ce Oferă

Fiecare acțiune importantă din platformă este înregistrată într-un **blockchain intern** (lanț de blocuri), asigurând:
- **Integritatea datelor** — orice modificare este detectabilă
- **Trasabilitate** — cine a făcut ce și când
- **Non-repudiere** — acțiunile nu pot fi negate

### 27.2 Tab-uri

| Tab | Descriere |
|-----|-----------|
| **Audit Trail** | Cronologia tuturor acțiunilor cu hash-uri blockchain |
| **Hash Documente** | Documente hash-uite pentru verificare integritate |
| **Verificare** | Verificare manuală hash document |
| **Chain of Custody** | Lanțul complet de custodiere a unui document |
| **Smart Contracts** | Verificări automate bazate pe reguli |

### 27.3 Verificare Document

1. Navigați la tab-ul **Hash Documente**
2. Încărcați un fișier sau introduceți hash-ul SHA-256
3. Platforma verifică dacă hash-ul există în blockchain
4. Rezultat: ✅ Verificat / ❌ Necunoscut

---

## 28. Administrare (Admin)

**Ruta:** `/admin` | **Vizibil doar pentru utilizatori cu rol admin**

### 28.1 Funcționalități Admin

- **Management utilizatori** — adaugă, dezactivează, modifică roluri
- **Management organizații** — configurare tenant-uri (multi-tenancy)
- **Monitorizare sincronizări** — status colectori de date
- **Configurare alerte** — praguri globale
- **Audit log** — jurnal complet al acțiunilor din platformă
- **Statistici de utilizare** — API calls, rapoarte generate, utilizatori activi

### 28.2 Roluri de Utilizator

| Rol | Permisiuni |
|-----|-----------|
| **viewer** | Doar vizualizare, fără modificare |
| **analyst** | Vizualizare + generare rapoarte + alerte |
| **admin** | Acces complet, inclusiv administrare |

---

## 29. Shortcuturi și Sfaturi

### Shortcuturi de Tastatură

| Shortcut | Acțiune |
|----------|---------|
| `Ctrl + K` | Deschide căutarea rapidă |
| `Esc` | Închide modal / dialog activ |

### Sfaturi de Utilizare

1. **Folosiți portofoliile** — grupați firmele pe categorii (clienți, furnizori, competiție) pentru monitorizare eficientă
2. **Configurați alerte** — nu rămâneți în urmă cu evenimentele importante
3. **Verificați Data Quality Score** — companiile cu scor mare (>70) au date mai complete și de încredere
4. **Folosiți AI Agent** — pentru întrebări complexe, asistentul AI economisește timp
5. **Exportați rapoarte** — pentru prezentări sau audit, generați PDF-uri profesionale
6. **Sidebar colapsibil** — apăsați meniul hamburger pentru a collapsa sidebar-ul și a avea mai mult spațiu

---

## 30. FAQ — Întrebări Frecvente

### Q: Cum adaug o firmă la monitorizare?
**A:** Căutați firma → deschideți profilul → apăsați „Adaugă în portofoliu" → selectați portofoliul dorit.

### Q: Cât de des se actualizează datele?
**A:** Datele se sincronizează periodic:
- **ANAF:** zilnic
- **ONRC:** zilnic
- **BPI:** zilnic
- **SEAP:** la fiecare 6 ore
- **BNR:** zilnic (cursuri valutare)
- **Portal Just:** săptămânal
- **AEGRM:** săptămânal

### Q: Ce înseamnă Data Quality Score?
**A:** Este un scor 0–100 care reflectă completitudinea datelor unei firme:
- **0–30:** Date de bază (doar identitate)
- **30–60:** Date moderate (+ financiare sau persoane)
- **60–85:** Date bune (+ risc, debts, contracte)
- **85–100:** Date complete (toate sursele sincronizate)

### Q: Cum funcționează scoring-ul de risc?
**A:** Scoring-ul de risc combină multiple criterii:
- Situație financiară (cifra de afaceri, profit, datorii)
- Istoric de plăți
- Litigii și insolvență
- Vechime firmă
- Status fiscal
- Activitate SEAP

Ratingul final: **A** (risc minim) → **E** (risc critic).

### Q: Datele sunt conforme GDPR?
**A:** Da. Platforma implementează:
- Anonimizarea CNP-urilor (afișare parțială)
- Dreptul la ștergere (right to be forgotten)
- Jurnal de acces la date personale
- Criptare la transport (TLS 1.2+)
- Multi-tenancy — datele unei organizații nu sunt vizibile altora

### Q: Pot integra datele în propriul meu sistem?
**A:** Da, prin API Marketplace. Generați o cheie API și folosiți endpoint-urile REST. Documentația completă este disponibilă la `/marketplace`.

### Q: Ce fac dacă am uitat parola?
**A:** Contactați administratorul organizației dvs. pentru resetarea parolei. Funcția de „Forgot password" va fi disponibilă în versiunile viitoare.

### Q: Cine poate vedea datele mele?
**A:** Doar utilizatorii din aceeași organizație. Platforma folosește multi-tenancy strict — fiecare organizație vede doar datele proprii (portofolii, rapoarte, alerte).

---

*Documentație generată pentru RomBiz Intelligence v1.0*  
*Pentru suport tehnic, contactați echipa de dezvoltare.*
