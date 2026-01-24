# 📋 GraphQL Dotazy pro Zápůjčky (Asset Loans)

## 🔐 Jako Administrátor

### 1️⃣ Vytvořit zápůjčku (půjčit někomu asset)

```graphql
mutation CreateLoan {
  assetLoanInsert(loan: {
    assetId: "UUID_ASSETU_TADY"
    borrowerUserId: "UUID_UZIVATELE_TADY"
    startdate: "2026-01-24T10:00:00"
    enddate: "2026-02-24T10:00:00"
    note: "Půjčeno pro projekt XYZ"
  }) {
    ... on AssetLoanGQLModel {
      id
      assetId
      borrowerUserId
      startdate
      enddate
      returned_date
      note
      asset {
        id
        name
        serial_number
      }
      borrower_user {
        id
        name
        surname
        email
      }
      borrower_user_email
      borrower_user_fullname
    }
    ... on InsertError {
      msg
      code
    }
  }
}
```

**Příklad s konkrétními ID:**
```graphql
mutation CreateLoanExample {
  assetLoanInsert(loan: {
    assetId: "123e4567-e89b-12d3-a456-426614174000"
    borrowerUserId: "76dac14f-7114-4bb2-882d-0d762eab6f4a"
    startdate: "2026-01-24T10:00:00"
    enddate: "2026-02-24T10:00:00"
    note: "Půjčeno pro testování"
  }) {
    ... on AssetLoanGQLModel {
      id
      assetId
      borrowerUserId
      startdate
      enddate
      note
    }
    ... on InsertError {
      msg
      code
    }
  }
}
```

---

### 2️⃣ Zobrazit všechny zápůjčky (admin vidí vše)

```graphql
query AllLoans {
  asset_loan_page(skip: 0, limit: 100) {
    id
    assetId
    borrowerUserId
    startdate
    enddate
    returned_date
    note
    asset {
      id
      name
      serial_number
      asset_type
    }
    borrower_user {
      id
      name
      surname
      email
    }
    borrower_user_email
    borrower_user_fullname
  }
}
```

---

### 3️⃣ Zobrazit zápůjčky konkrétního uživatele (admin)

```graphql
query UserLoans($userId: UUID!) {
  asset_loan_page(
    skip: 0
    limit: 100
    where: {
      borrowerUserId: $userId
    }
  ) {
    id
    assetId
    borrowerUserId
    startdate
    enddate
    returned_date
    note
    asset {
      id
      name
      serial_number
    }
    borrower_user_email
    borrower_user_fullname
  }
}
```

**Variables:**
```json
{
  "userId": "76dac14f-7114-4bb2-882d-0d762eab6f4a"
}
```

---

### 4️⃣ Zobrazit zápůjčky přes User typ (admin)

```graphql
query UserWithLoans($userId: UUID!) {
  user(id: $userId) {
    id
    name
    surname
    email
    asset_loans {
      id
      assetId
      startdate
      enddate
      returned_date
      note
      asset {
        id
        name
        serial_number
      }
    }
  }
}
```

**Variables:**
```json
{
  "userId": "76dac14f-7114-4bb2-882d-0d762eab6f4a"
}
```

---

## 👤 Jako běžný uživatel (viewer/editor)

### 5️⃣ Zobrazit své zápůjčky

```graphql
query MyLoans {
  asset_loan_page(skip: 0, limit: 100) {
    id
    assetId
    borrowerUserId
    startdate
    enddate
    returned_date
    note
    asset {
      id
      name
      serial_number
      asset_type
      description
    }
    borrower_user_email
    borrower_user_fullname
  }
}
```

**Poznámka:** Běžný uživatel vidí pouze své vlastní zápůjčky (kde je `borrowerUserId` = jeho ID).

---

### 6️⃣ Zobrazit své zápůjčky přes whoAmI

```graphql
query MyLoansViaWhoAmI {
  whoAmI {
    id
    email
    name
    surname
  }
  # Poznámka: User.asset_loans není dostupné přes whoAmI, použijte asset_loan_page
}
```

---

## 🔍 Pomocné dotazy

### 7️⃣ Najít dostupné assety pro půjčení

```graphql
query AvailableAssets {
  assetPage(skip: 0, limit: 100) {
    id
    name
    serial_number
    asset_type
    status
    description
    loans {
      id
      startdate
      enddate
      returned_date
    }
  }
}
```

**Poznámka:** Zkontrolujte pole `loans` - pokud `returned_date` je `null` a `enddate` je v budoucnosti, asset je aktuálně půjčený.

---

### 8️⃣ Najít uživatele pro půjčení

```graphql
query FindUsers {
  users(skip: 0, limit: 100) {
    id
    name
    surname
    email
  }
}
```

**Poznámka:** Tento dotaz může být dostupný pouze v `gql_ug` subgraphu, ne v `evolution` subgraphu.

---

## ✏️ Update zápůjčky (označit jako vrácenou)

```graphql
mutation ReturnLoan($loanId: UUID!, $lastchange: DateTime!) {
  assetLoanUpdate(loan: {
    id: $loanId
    lastchange: $lastchange
    returned_date: "2026-01-24T15:00:00"
    note: "Vráceno v pořádku"
  }) {
    ... on AssetLoanGQLModel {
      id
      returned_date
      note
    }
    ... on UpdateError {
      msg
      code
    }
  }
}
```

**Variables:**
```json
{
  "loanId": "UUID_ZAPUJCKY",
  "lastchange": "2026-01-24T14:30:00"
}
```

---

## 🗑️ Smazat zápůjčku

```graphql
mutation DeleteLoan($loanId: UUID!, $lastchange: DateTime!) {
  assetLoanDelete(loan: {
    id: $loanId
    lastchange: $lastchange
  }) {
    id
    msg
  }
}
```

---

## 📝 Poznámky

1. **Pouze administrátor** může vytvářet, upravovat a mazat zápůjčky
2. **Běžný uživatel** může vidět pouze své vlastní zápůjčky
3. **ID assetu** získáte z `assetPage` query
4. **ID uživatele** získáte z `whoAmI` query nebo z frontendu
5. **Datum formát:** `"YYYY-MM-DDTHH:mm:ss"` (ISO 8601)

---

## 🎯 Rychlý workflow

1. **Najít asset ID:**
   ```graphql
   query { assetPage(skip: 0, limit: 10) { id name } }
   ```

2. **Najít user ID:**
   ```graphql
   query { whoAmI { id email } } }
   ```
   Nebo použijte ID z frontendu.

3. **Vytvořit zápůjčku:**
   ```graphql
   mutation {
     assetLoanInsert(loan: {
       assetId: "..."
       borrowerUserId: "..."
       startdate: "2026-01-24T10:00:00"
       enddate: "2026-02-24T10:00:00"
     }) { ... on AssetLoanGQLModel { id } }
   }
   ```

4. **Zobrazit zápůjčky:**
   ```graphql
   query { asset_loan_page(skip: 0, limit: 100) { id asset { name } } }
   ```
