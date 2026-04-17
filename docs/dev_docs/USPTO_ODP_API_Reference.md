# USPTO Open Data Portal (ODP) API Reference

Comprehensive reference for the USPTO ODP REST API as of 2026-04-17.

## Authentication

All requests require an API key in the `X-API-KEY` header.

```
X-API-KEY: <your-key>
```

- Register at [data.uspto.gov](https://data.uspto.gov) to obtain a key.
- Store in the `USPTO_API_KEY` environment variable.
- Requests without a valid key return 401.

## Base URL

```
https://api.uspto.gov/api/v1
```

## Rate Limits

| Quota              | Limit                   |
|--------------------|-------------------------|
| Metadata per week  | 5,000,000 requests      |
| Documents per week | 1,200,000 requests      |
| Burst              | 1 concurrent request    |
| Sustained rate     | 4-15 requests/second    |
| Reset              | Sunday 00:00 UTC        |

Exceeding limits returns 429. Back off and retry with exponential delay.

---

## Endpoint Catalog (48 endpoints)

### Patent Application API (15 paths)

| Method | Path                                                   | Description                          |
|--------|--------------------------------------------------------|--------------------------------------|
| GET    | /patent/applications/search                            | Search applications (query string)   |
| POST   | /patent/applications/search                            | Search applications (body)           |
| GET    | /patent/applications/{appNumTxt}/meta-data             | Application metadata                 |
| GET    | /patent/applications/{appNumTxt}/continuity            | Continuity/parent-child chain        |
| GET    | /patent/applications/{appNumTxt}/adjustment            | Patent term adjustment (PTA)         |
| GET    | /patent/applications/{appNumTxt}/foreign-priority      | Foreign priority claims              |
| GET    | /patent/applications/{appNumTxt}/associated-documents  | Grant XML, pub XML, PDFs             |
| GET    | /patent/applications/{appNumTxt}/assignment            | **SINGULAR** -- assignment chain     |
| GET    | /patent/applications/{appNumTxt}/transactions          | Prosecution history / IFW events     |
| GET    | /patent/applications/{appNumTxt}/attorney              | Attorney/agent of record             |
| GET    | /patent/applications/{appNumTxt}/documents             | Document list (office actions, etc.) |
| GET    | /patent/applications/{appNumTxt}/status-codes          | Application status code history      |
| GET    | /patent/applications/search/download                   | Bulk download search results         |
| POST   | /patent/applications/search/download                   | Bulk download search results (body)  |
| POST   | /patent/applications/text-to-search                    | **DEFUNCT** -- NLP query translation  |

> **CRITICAL:** The assignment endpoint is `/assignment` (singular).
> `/assignments` (plural) returns **403 Forbidden**. The Swagger documentation
> is misleading on this point.

### Download Endpoints (4 paths)

| Method | Path                                                              | Description             |
|--------|-------------------------------------------------------------------|-------------------------|
| GET    | /patent/applications/{appNumTxt}/documents/{mailRoomDt}/{docCode} | Download PDF document   |
| GET    | /patent/applications/{appNumTxt}/archive                          | Download XML archive    |
| GET    | /patent/grants/{patentNumber}/document                            | Download grant XML      |
| GET    | /patent/publications/{pubNumber}/document                         | Download pre-grant pub XML |

### Bulk Data API (3 paths)

| Method | Path                            | Description                    |
|--------|---------------------------------|--------------------------------|
| GET    | /bulk-data/search               | Search available bulk products |
| GET    | /bulk-data/product/{productId}  | Product metadata               |
| GET    | /bulk-data/download/{fileId}    | Download bulk data file        |

### Petition API (3 paths)

| Method | Path                                   | Description              |
|--------|----------------------------------------|--------------------------|
| GET    | /patent/petitions/search               | Search petition decisions |
| GET    | /patent/petitions/{petitionId}         | Decision data            |
| GET    | /patent/petitions/{petitionId}/download| Download petition PDF    |

### PTAB Trials (11 paths)

| Method | Path                                                     | Description                    |
|--------|----------------------------------------------------------|--------------------------------|
| GET    | /ptab/proceedings/search                                 | Search PTAB proceedings        |
| GET    | /ptab/proceedings/{proceedingId}                         | Proceeding details             |
| GET    | /ptab/decisions/search                                   | Search PTAB decisions          |
| GET    | /ptab/decisions/{decisionId}                             | Decision details               |
| GET    | /ptab/documents/search                                   | Search PTAB documents          |
| GET    | /ptab/documents/{documentId}/download                    | Download PTAB document         |
| GET    | /ptab/trials/{trialId}/documents                         | Documents by trial             |
| GET    | /ptab/trials/{trialId}/documents/{documentId}            | Specific document by trial     |
| GET    | /ptab/appeals/search                                     | Search PTAB appeals            |
| GET    | /ptab/appeals/{appealId}/download                        | Download appeal document       |
| GET    | /ptab/appeals/{appealId}/documents/{documentId}          | Specific document by appeal    |

### PTAB Appeals (4 paths)

| Method | Path                                                       | Description                 |
|--------|------------------------------------------------------------|-----------------------------|
| GET    | /ptab/appeals/search                                       | Search appeals              |
| GET    | /ptab/appeals/{appealId}/download                          | Download appeal decision    |
| GET    | /ptab/appeals/{appealId}/documents/{documentId}            | Document by appeal + doc ID |
| GET    | /ptab/appeals/{appealId}                                   | Appeal details              |

### PTAB Interferences (4 paths)

| Method | Path                                                              | Description                      |
|--------|-------------------------------------------------------------------|----------------------------------|
| GET    | /ptab/interferences/search                                        | Search interferences             |
| GET    | /ptab/interferences/{interferenceId}/download                     | Download interference document   |
| GET    | /ptab/interferences/{interferenceId}/documents/{documentId}       | Document by interference + doc   |
| GET    | /ptab/interferences/{interferenceId}                              | Interference details             |

### Office Action DSAPI (8 paths)

| Method | Path                                      | Description                        |
|--------|-------------------------------------------|------------------------------------|
| GET    | /dsapi/oa-text/fields                     | OA text retrieval -- field list    |
| POST   | /dsapi/oa-text/records                    | OA text retrieval -- search        |
| GET    | /dsapi/oa-citations/fields                | OA citations -- field list         |
| POST   | /dsapi/oa-citations/records               | OA citations -- search             |
| GET    | /dsapi/oa-rejections/fields               | OA rejections -- field list        |
| POST   | /dsapi/oa-rejections/records              | OA rejections -- search            |
| GET    | /dsapi/enriched-citations/fields          | Enriched citations -- field list   |
| POST   | /dsapi/enriched-citations/records         | Enriched citations -- search       |

DSAPI endpoints accept Lucene query syntax in the POST body and return
paginated results with `offset` and `limit` parameters.

---

## Search Query Syntax

### Free-form Search

```
GET /patent/applications/search?searchText=autonomous+vehicle+lidar
```

### Field-specific Query

```
GET /patent/applications/search?searchText=applicationMetaData.patentNumber:9629826
```

Common queryable fields:

- `applicationMetaData.patentNumber` -- grant number (digits only, no prefix)
- `applicationMetaData.earliestPublicationNumber` -- pre-grant pub number
- `applicationMetaData.applicationNumberText` -- application number
- `applicationMetaData.inventionTitle` -- title keywords
- `applicationMetaData.filingDate` -- filing date (YYYY-MM-DD)

### Boolean Operators

```
searchText=(autonomous AND vehicle) OR lidar
searchText=autonomous AND NOT drone
```

### Wildcard

```
searchText=applicationMetaData.inventionTitle:neural*
```

### Range Query

```
searchText=applicationMetaData.filingDate:[2020-01-01 TO 2024-12-31]
```

### Phrase Query

```
searchText="machine learning model"
```

---

## Fields Parameter

The `fields` query parameter controls which data is returned. It is
**case-sensitive** and supports wildcards.

```
GET /patent/applications/search?searchText=...&fields=applicationMetaData.*,applicationNumberText
```

Omitting `fields` returns the default subset. Use `fields=*` for everything
(large response).

---

## Response Schema

All application endpoints return a `patentFileWrapperDataBag` wrapper:

```json
{
  "patentFileWrapperDataBag": {
    "applicationNumberText": "14966067",
    "applicationMetaData": {
      "patentNumber": "9629826",
      "inventionTitle": "...",
      "filingDate": "2016-12-12",
      "grantDate": "2017-04-25",
      "earliestPublicationNumber": "..."
    },
    "assignmentBag": [ ... ],
    "eventDataBag": [ ... ],
    "continuityBag": { ... },
    "foreignPriorityBag": [ ... ],
    "adjustmentDataBag": { ... },
    "associatedDocumentsBag": { ... }
  }
}
```

Key sub-objects:

- `assignmentBag` -- array of assignment records with `assignorName`,
  `assigneeName`, `conveyanceText`, `reelNumber`, `frameNumber`
- `eventDataBag` -- array of transaction records with `eventCode`,
  `eventDescriptionText`, `eventDate`
- `associatedDocumentsBag` -- contains `grantDocumentMetaData` with
  `fileLocationURI` for grant XML download

---

## Claims Extraction Recipe

ODP has no dedicated claims endpoint. Extract claims from grant XML:

1. Fetch associated documents:

   ```
   GET /patent/applications/{appNumTxt}/associated-documents
   ```

2. Extract the grant XML URI from the response:

   ```
   response.associatedDocumentsBag.grantDocumentMetaData.fileLocationURI
   ```

3. Download the grant XML from that URI.

4. Parse the `<claims>` element:

   ```xml
   <claims>
     <claim id="CLM-00001" num="1">
       <claim-text>A method comprising...</claim-text>
     </claim>
     <claim id="CLM-00002" num="2">
       <claim-text>The method of claim 1, wherein...</claim-text>
     </claim>
   </claims>
   ```

5. Independent claims have no "claim N" dependency reference in their text.
   Dependent claims reference a parent claim number.

---

## Patent Number Resolution

Users provide patent numbers in various formats. Resolution strategy:

### Grant Number (e.g., US9629826B2)

1. Strip prefix "US" and suffix letter+digit (e.g., "B2").
2. Search: `applicationMetaData.patentNumber:9629826`
3. Return `applicationNumberText` from the result.

### Application Number (e.g., 14/966,067)

1. Strip all punctuation: `14966067`.
2. Use directly as `applicationNumberText` (passthrough).

### Publication Number (e.g., US20170168565A1)

1. Strip prefix "US" and suffix letter+digit.
2. Search: `applicationMetaData.earliestPublicationNumber:20170168565`
3. Return `applicationNumberText` from the result.

---

## PatentsView Status

**Dead as of 2026-03-20.** The PatentsView API (api.patentsview.org) was
decommissioned when its data migrated to ODP. All endpoints return 404.
Do not build against PatentsView. Use ODP exclusively.

---

## Enriched Citations

The DSAPI enriched-citations endpoint returns prior art citations with
examiner-assigned category codes:

| Code | Meaning                                        |
|------|------------------------------------------------|
| X    | Particularly relevant if taken alone           |
| Y    | Particularly relevant if combined with another |
| A    | General technological background               |
| E    | Earlier document with later publication date   |

Query example (POST to `/dsapi/enriched-citations/records`):

```json
{
  "query": "applicationNumberText:14966067",
  "offset": 0,
  "limit": 25
}
```

---

## Swagger Gotchas

Known discrepancies between the Swagger/OpenAPI spec and actual API behavior:

1. **frameNumber / reelNumber**: Swagger shows `string`, but the API returns
   `integer`. Parse accordingly.

2. **correspondenceAddress**: Swagger shows an `array`, but the API returns a
   single `object`. Do not iterate over it.

3. **/assignment vs /assignments**: The correct path is `/assignment`
   (singular). `/assignments` (plural) returns **403 Forbidden**. This is the
   single most common integration error.

4. **text-to-search**: Listed in Swagger but defunct. Returns errors or empty
   results. Do not use.

---

## External References

- [USPTO Open Data Portal](https://data.uspto.gov) -- API key registration,
  documentation, and Swagger UI
- [patent-dev/uspto-odp](https://github.com/patent-dev/uspto-odp) -- Go client
  library for ODP (community-maintained)
