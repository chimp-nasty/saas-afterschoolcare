# Child document storage and retention policy

**Status:** Draft v0.1 (20 October 2026). Not legal advice. Have it reviewed by a privacy lawyer before the first tenant goes live, and check every regulation reference marked *verify* against the current text.

**Applies to:** documents families upload about their children (medical, asthma and allergy/anaphylaxis action plans, and other supporting documents), stored in the child documents storage bucket, and the `public.child_documents` rows that describe them.

**Provider:** the requirements here don't depend on the storage provider. Google Cloud Storage (GCS) is the default; Amazon S3 is supported as an alternative. Sections 7 and 15 give each provider's configuration. The app chooses the provider with the `STORAGE_PROVIDER` setting, and each document row records which provider and bucket hold it.

**Does not cover:** the medical text on `child_profile` (`medical_info`, `allergy_info`, `medication_info`), attendance, incident, medication administration or billing records. Those need their own retention rules (see [Related records](#related-records)).

---

## 1. Purpose

Children's medical documents are **health information**, which is **sensitive information** under the *Privacy Act 1988* (Cth). This policy sets out how we store, protect, keep and destroy them so that:

- each approved provider (our tenant) can meet its record-keeping duties under the *Education and Care Services National Law* and *Regulations*
- we meet the Australian Privacy Principles (APPs), especially APP 11 (security, and destroying information no longer needed)
- families know what happens to what they upload.

## 2. Roles

| Party | Role |
|---|---|
| **Approved provider (tenant)** | Owns the records. Holds the regulatory duty to keep them (reg 183, *verify*) and decides what is collected. |
| **Us (the platform)** | Stores and processes the records for the tenant under our service agreement. Runs the controls in this policy. |
| **Families** | Upload documents and can see, replace and remove their own children's documents in the app. |
| **Centre staff and admins** | Read documents to review a child's medical needs. They can't upload, change or delete documents. |
| **Google Cloud** | Infrastructure provider (storage) under the Google Cloud Data Processing Addendum. |

## 3. Principles

1. **Australia only.** Documents, their metadata and their backups are stored only in Australian regions.
2. **Least access.** Only the family and staff at the child's centre can reach a document. There is no public access, ever.
3. **Keep only as long as required.** Records are kept for the longest period the law requires, then destroyed (APP 11.2). We don't keep them "just in case".
4. **No personal information in names.** Bucket and object names contain only random IDs. Google's data-location commitments don't cover resource names, and names show up in logs.
5. **Rules live in one place.** Retention dates are worked out in the database, which knows attendance. The bucket's lifecycle rules only clean up abandoned uploads; they never decide when a real record expires.

## 4. Where documents are stored

| Control | Setting | Why |
|---|---|---|
| Location | GCS: `australia-southeast1` (Sydney), single region; a Sydney + Melbourne dual-region is optional for geographic redundancy. S3: `ap-southeast-2` (Sydney). | Keeps data onshore and limits APP 8 exposure |
| Organisation policy | GCS: `gcp.resourceLocations` = `in:au-locations`. S3: an organisation policy (SCP) that denies regions outside Australia. | Stops anyone creating resources outside Australia |
| Access model | GCS: uniform bucket-level access, public access prevention enforced. S3: Block Public Access on, Object Ownership "bucket owner enforced" (ACLs off). | No object ACLs and no public links |
| Who can read and write | Only the API's service account. Nobody else has standing access to objects. | Every access passes our permission and row-level checks |
| How families and staff reach files | Signed upload policies (POST, valid 15 minutes, size and type enforced by the provider) and signed download URLs (5 minutes), issued only after a permission and RLS check | A leaked link stops working within minutes, and oversized or wrong-type uploads are rejected before they're stored |
| Encryption | At rest with provider-managed keys. Customer-managed keys (GCS: CMEK in Cloud KMS; S3: SSE-KMS; both in Sydney) if a tenant requires them. In transit with TLS only. | Required by APP 11; customer-managed keys also allow destroying data by destroying the key |
| Versioning | GCS: off. S3: on, solely to provide soft delete (below). | Superseded documents are kept as separate records, not hidden versions |
| Soft delete | 7 days. GCS: built-in soft delete. S3: noncurrent versions and delete markers expire after 7 days. | Lets us recover from an accidental purge without keeping data long after destruction |
| Bucket lock / retention lock | **Not used** | It would stop us destroying records on time |
| Audit logs | Cloud Audit Logs *Data Access* logging on for the bucket, stored in an Australian log bucket. The API also logs every signed URL it issues (user, child and document IDs only). | Supports breach investigation and access requests |

### Tenants share one bucket

Every tenant's documents are kept in one shared bucket. The APPs don't require tenants' data to be physically separated: APP 11 requires reasonable steps, and logical separation with the controls below is the standard approach for multi-tenant software.

| Control | How |
|---|---|
| **The database is the catalogue** | Every object has a `child_documents` row, and row-level security decides who can see that row. Nobody lists or browses the bucket. |
| **Keys are built only by the server** | The API never accepts a bucket name or object key from a client. It only signs the key stored on a row the caller is allowed to read. |
| **A second check before signing** | Before signing a link, the storage layer confirms the key starts with the row's own tenant and location prefix. A query bug therefore can't hand out another tenant's file. |
| **Keys start with the tenant** | See object naming below. A tenant's export and destruction work on its own prefix. |
| **Objects carry their owner's IDs** | Each object has `tenant_id`, `location_id`, `child_id` and `document_id` as metadata (IDs only), so a stray object can be traced back to its owner. |
| **A tenant can move to its own bucket** | Each row records its provider and bucket. If a tenant needs a dedicated bucket or its own encryption key, its prefix is copied across and its rows updated, with no schema change. |

The main remaining risk is a cross-tenant leak caused by an application bug. Row-level security plus the check before signing cover it, and the tests check that one tenant can't reach another's documents.

### Object naming

Names contain only random IDs, never personal details or tenant codes (a tenant code can identify a business).

```
pending/tenants/{tenant_id}/{document_id}                                                  upload in progress
documents/tenants/{tenant_id}/locations/{location_id}/children/{child_id}/{document_id}    accepted document
```

Uploads land under `pending/`. When the upload is completed, the API checks the file's real size, type and first bytes (PDF, JPEG, PNG or HEIC; at most 10 MB), then copies it to `documents/…` and deletes the pending object. A file that fails the check is deleted and its row marked `failed`. The original file name is kept only in the database, so it can be shown to the family.

## 5. Retention periods

The *Education and Care Services National Regulations* (reg 183, *verify*) set minimum periods for keeping records about a child:

| Record | Kept until | Source |
|---|---|---|
| Records relating to a child generally (enrolment records, medical management and action plans, medication records) | **3 years after the last day the child attended the service** | reg 183(2), *verify* |
| Records relating to an incident, injury, trauma or illness while the child was being cared for | **Until the child turns 25** | reg 183(2), *verify* |
| Records relating to the death of a child while being cared for | **7 years after the child's death** | reg 183(2), *verify* |

### How the rules apply to child documents

1. **While the child is enrolled**, every document is kept, including documents the family has removed or replaced. A removed action plan may be needed to show which plan the centre held at a given time. Removed documents disappear from the family's and staff's normal views, but the record stays.
2. **Retention end date** = 3 years after the child's **last attendance** (the latest sign-in in `attendance_records`).
   - **If the child never attended**, the date is 3 years after the later of the child's removal and the document's upload. Such a document may not count as a record of education and care, but keeping it for the same period is the cautious choice.
3. **Extended retention:**
   - If the child has an incident, injury, trauma or illness record at the service, their documents are kept **until the child turns 25**.
   - If a child dies while being cared for, their documents are kept **7 years after the death**.
4. **Legal hold:** a tenant admin or the platform can place a hold on a child (litigation, complaint, regulator investigation or breach investigation). Nothing is destroyed while a hold is in place. Holds are recorded with a reason and reviewed at least every 12 months.
5. **Destruction:** once the retention end date has passed and there's no hold, the document is destroyed within **30 days**.

### Uploads that never finish

| What | Removed after | Done by |
|---|---|---|
| Objects under `pending/` | 1 day | Bucket lifecycle rule (section 7) |
| `child_documents` rows still `pending` | 1 day (marked `failed`) | Daily database job |
| Rows marked `failed` | 30 days (row deleted; the object never existed or was already removed) | Daily database job |

## 6. Destruction

Destruction is run by a **daily retention job** in the API, not by bucket lifecycle rules, because only the database knows attendance and holds. For each document due for destruction, the job:

1. deletes the object from the bucket
2. **de-identifies** the row: sets `purged_at`, clears the file name, size and object key, and keeps the ID, child ID, document type and dates as a tombstone that proves the record existed and was destroyed on time
3. logs the destruction (document ID, child ID, date, reason: "retention period ended").

The object stays recoverable through soft delete for 7 days and then is gone permanently. If CMEK is in use and a tenant leaves, destroying that tenant's key makes any remaining copies unreadable.

Destroying the child's profile and other records is handled under the child-record retention rules (see [Related records](#related-records)), not by this job.

## 7. Bucket configuration (GCS)

The lifecycle rules only clean up abandoned uploads. Real records under `documents/` are **never** deleted by lifecycle rules (see principle 5). The S3 equivalent is in section 15.

The files below are kept in `deploy/storage/gcs/`, with a CORS file per environment (`child-documents-cors.dev.json` for local development).

`child-documents-lifecycle.json`:

```json
{
  "lifecycle": {
    "rule": [
      {
        "action": { "type": "Delete" },
        "condition": { "age": 1, "matchesPrefix": ["pending/"] }
      },
      {
        "action": { "type": "AbortIncompleteMultipartUpload" },
        "condition": { "age": 1 }
      }
    ]
  }
}
```

`age` is in days, and Google applies rules asynchronously, so cleanup can lag by up to about a day. Storage class stays **Standard**: the files are small, and colder classes' minimum storage periods and retrieval fees outweigh the savings.

### Creating the bucket

The bucket name holds no tenant or personal details. Replace `<bucket>` and `<frontend-origin>`.

```sh
gcloud storage buckets create gs://<bucket> \
  --location=australia-southeast1 \
  --default-storage-class=STANDARD \
  --uniform-bucket-level-access \
  --public-access-prevention \
  --soft-delete-duration=7d

gcloud storage buckets update gs://<bucket> \
  --lifecycle-file=child-documents-lifecycle.json \
  --cors-file=child-documents-cors.json
```

`child-documents-cors.json` (browser uploads and downloads from the app only):

```json
[
  {
    "origin": ["<frontend-origin>"],
    "method": ["POST", "GET"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
```

Also needed outside the bucket:

- Data Access audit logs turned on for Cloud Storage.
- The organisation's default log storage location set to Australia.
- The API's service account given `roles/storage.objectAdmin` on this bucket only, plus `roles/iam.serviceAccountTokenCreator` on itself so it can sign URLs.

## 8. Family requests

| Request | Response |
|---|---|
| **Access** (APP 12) | Families can see and download their own children's current documents in the app at any time. Requests for removed documents or access logs go to the centre, which responds within 30 days. |
| **Correction** (APP 13) | The family uploads a replacement and removes the old one. The old document is kept under section 5. |
| **Deletion** | Australian law has no general right to erasure, and the National Regulations require these records to be kept. We remove the document from view immediately, explain the retention period, and destroy it when that period ends (section 6). |
| **Child leaves or account closed** | Documents are kept until the retention end date, then destroyed. They stay readable to the centre's staff for that period. |

## 9. When a tenant leaves

The tenant owns the records and stays bound by the retention rules after it stops using the platform (reg 183 and 184, *verify*). When a tenant leaves:

1. we give the tenant a complete export (documents plus an index of child, type and dates) within 30 days
2. after the tenant confirms in writing that it has received the export, we destroy all of its documents under section 6 (and destroy the key, if it uses CMEK)
3. the destruction is recorded and confirmed to the tenant in writing.

## 10. Breaches

A suspected unauthorised access to, disclosure of or loss of documents is handled under the Notifiable Data Breaches scheme:

- contain the breach immediately
- assess it within 30 days
- if serious harm is likely, notify the OAIC and the affected families as soon as practicable (in practice, through the tenant)
- tell the affected tenant immediately in every case.

Audit logs (section 4) are kept long enough to investigate: at least 2 years.

## 11. Overseas access and privacy notice

Data is stored only in Australia. Unless we take up Google's *Assured Workloads – Australia Data Boundary and Support* package, Google support staff may access systems from overseas under Google's data processing terms.

Each tenant's privacy policy and collection notice (APP 1 and APP 5) should say:

- that documents are stored in Australia, and which providers hold them (Google Cloud for files; Neon on AWS Sydney for database records; AWS SES Sydney for email)
- that service providers' support staff may access data from overseas
- who sees the documents (centre staff, to plan for the child's care)
- the retention periods in section 5
- how to make an access or correction request, or a complaint.

Emails never contain health details or document links that work without logging in.

## 12. Related records

These need retention rules of their own, to be added to this folder as they're built:

- **Child profile medical text:** same 3-year / age-25 rules as section 5. Destroying it means de-identifying the profile.
- **Medication administration and incident records:** not built yet. Their existence triggers the age-25 rule in section 5.
- **Attendance records:** needed to calculate the retention end date, so they're kept at least as long as the documents they date.
- **Payment records:** tax law (5 years) applies, separately.

## 13. Implementation status

| Control | Status |
|---|---|
| Bucket in Sydney, uniform access, public access prevention, soft delete 7 days | To do when the bucket is created |
| Lifecycle rules (section 7) | To do when the bucket is created |
| Organisation location policy, log location, Data Access logs | To do (Google Cloud org setup) |
| Upload under `pending/`, checks on completion, copy to `documents/` | Slice 2 |
| Signed URLs issued after permission and RLS checks, audit logging of URLs | Slice 2 |
| Family-only uploads, staff read-only | Slice 2 |
| `failed` / abandoned upload cleanup job | Later (no hard deadline; lifecycle rules cover the objects) |
| Retention end date, legal holds, `purged_at` tombstones, daily destruction job | Later. Must exist before any child has been gone for 3 years. |
| Tenant exit export | Later, with tenant configuration |

## 14. Review

This policy is reviewed every year, and also when the National Regulations or Privacy Act change, when a new storage provider or region is used, or after any breach.

## 15. Appendix: Amazon S3 configuration

The same rules as section 7, for when `STORAGE_PROVIDER=s3`. Replace `<bucket>`, `<frontend-origin>` and `<account-id>`.

```sh
aws s3api create-bucket --bucket <bucket> --region ap-southeast-2 \
  --create-bucket-configuration LocationConstraint=ap-southeast-2

aws s3api put-public-access-block --bucket <bucket> \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

aws s3api put-bucket-ownership-controls --bucket <bucket> \
  --ownership-controls 'Rules=[{ObjectOwnership=BucketOwnerEnforced}]'

aws s3api put-bucket-encryption --bucket <bucket> \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"},"BucketKeyEnabled":true}]}'

aws s3api put-bucket-versioning --bucket <bucket> \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-lifecycle-configuration --bucket <bucket> \
  --lifecycle-configuration file://child-documents-lifecycle.s3.json

aws s3api put-bucket-cors --bucket <bucket> \
  --cors-configuration file://child-documents-cors.s3.json
```

To use a customer-managed key, use `"SSEAlgorithm":"aws:kms"` with a KMS key in `ap-southeast-2`.

`child-documents-lifecycle.s3.json`: clears abandoned uploads, and gives the 7-day soft delete (versioning keeps a deleted object as a noncurrent version for 7 days, then it's gone):

```json
{
  "Rules": [
    {
      "ID": "pending-uploads",
      "Filter": { "Prefix": "pending/" },
      "Status": "Enabled",
      "Expiration": { "Days": 1 },
      "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 1 }
    },
    {
      "ID": "soft-delete-window",
      "Filter": {},
      "Status": "Enabled",
      "NoncurrentVersionExpiration": { "NoncurrentDays": 7 },
      "Expiration": { "ExpiredObjectDeleteMarker": true }
    }
  ]
}
```

`child-documents-cors.s3.json`:

```json
{
  "CORSRules": [
    {
      "AllowedOrigins": ["<frontend-origin>"],
      "AllowedMethods": ["POST", "GET"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3600
    }
  ]
}
```

Also needed:

- CloudTrail data events for the bucket (the equivalent of Data Access audit logs), stored in `ap-southeast-2`.
- The API's IAM role limited to `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` and `s3:ListBucket` on this bucket only.
