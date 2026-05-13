# RomBiz Intelligence API

## Base URL
```
https://api.rombiz.ro/api/v1
```

## Autentificare
Toate endpoint-urile (excépție: auth) necesita header:
```
Authorization: Bearer <jwt_token>
```

JWT-urile sunt semnate RS256. Token-ul expiră în 30 minute, refresh token-ul în 7 zile.

## Endpoints

### Auth
| Metoda | Path | Descriere |
|--------|------|-----------|
| POST | /auth/register | Înregistrare cont nou |
| POST | /auth/login | Autentificare (returnează access + refresh token) |
| POST | /auth/refresh | Reînnoire token |
| GET | /auth/me | Profil utilizator curent |

### Companii
| Metoda | Path | Descriere |
|--------|------|-----------|
| GET | /companies/{cui} | Profil complet companie |
| GET | /companies/{cui}/financials | Date financiare (bilanțuri) |
| GET | /companies/{cui}/risk | Scor de risc + detalii |
| GET | /companies/{cui}/persons | Asociați și administratori |
| GET | /companies/{cui}/court-cases | Dosare instanțe |
| GET | /companies/{cui}/insolvency | Cazuri insolvență |
| GET | /companies/{cui}/contracts | Contracte publice |
| GET | /companies/{cui}/debts | Datorii restante |

### Căutare
| Metoda | Path | Descriere |
|--------|------|-----------|
| GET | /search?q=&judet=&stare=&caen= | Căutare full-text cu filtre |

### Risc
| Metoda | Path | Descriere |
|--------|------|-----------|
| GET | /risk/{cui} | Scor risc curent |
| GET | /risk/{cui}/history | Istoric scoruri |
| POST | /risk/{cui}/recalculate | Recalculare forțată |

### ESG
| Metoda | Path | Descriere |
|--------|------|-----------|
| GET | /esg/{cui} | Scor ESG curent + disclaimer |
| GET | /esg/ranking?sector=&limit= | Top companii ESG |

### Fraud Graph
| Metoda | Path | Descriere |
|--------|------|-----------|
| GET | /fraud/{cui} | Profil fraud (anomaly score, alerte) |
| GET | /fraud/{cui}/graph | Subgraph relații (noduri + muchii) |

### Alerte
| Metoda | Path | Descriere |
|--------|------|-----------|
| GET | /alerts | Lista alerte utilizator |
| PUT | /alerts/{id}/read | Marchează ca citită |
| PUT | /alerts/read-all | Marchează toate ca citite |
| WS | /alerts/ws | WebSocket real-time alerts |

### Portofolii
| Metoda | Path | Descriere |
|--------|------|-----------|
| GET | /portfolios | Lista portofolii |
| POST | /portfolios | Creare portofoliu |
| POST | /portfolios/{id}/companies | Adaugă companie în portofoliu |
| GET | /portfolios/{id}/risk-summary | Sumar risc portofoliu |

### RedBill
| Metoda | Path | Descriere |
|--------|------|-----------|
| GET | /redbill/{cui} | Profil datorii restante |
| POST | /redbill/{cui}/report | Generare raport datorii |

### SEAP
| Metoda | Path | Descriere |
|--------|------|-----------|
| GET | /seap/tenders | Licitații active (filtru CPV, valoare, dată) |

### Rapoarte
| Metoda | Path | Descriere |
|--------|------|-----------|
| POST | /reports/company/{cui} | Generare raport companie (PDF/Excel) |
| POST | /reports/portfolio/{id} | Generare raport portofoliu |
| GET | /reports/exports | Lista exporturi |
| GET | /reports/download/{file_id} | Descărcare fișier |

### Admin (rol: admin)
| Metoda | Path | Descriere |
|--------|------|-----------|
| GET | /admin/dashboard | Dashboard admin |
| GET | /admin/data-sources | Health surse de date |
| POST | /admin/sync/{source} | Trigger sync manual |
| GET | /admin/audit-log | Audit log |

### AI Agent
| Metoda | Path | Descriere |
|--------|------|-----------|
| POST | /ai-agent/query | Întrebare în limbaj natural |

### Companii Noi
| Metoda | Path | Descriere |
|--------|------|-----------|
| GET | /new-companies | Feed firme noi (filtru județ, CAEN, data) |
| GET | /new-companies/stats | Statistici înregistrări noi |

## Coduri de Eroare

| Cod | Descriere |
|-----|-----------|
| 400 | Request invalid (validare eșuată) |
| 401 | Token expirat sau invalid |
| 403 | Acces interzis (rol insuficient) |
| 404 | Resursă negăsită |
| 422 | Validare eșuată (CUI invalid, etc.) |
| 429 | Rate limit depășit |
| 500 | Eroare internă server |

## Rate Limiting
- API general: 30 requests/secundă
- Auth endpoints: 5 requests/secundă
- Configurat via Nginx
