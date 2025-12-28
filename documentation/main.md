# WorkflowAutom — Platform & Environment Lifecycle Design

## 1. Purpose & Motivation

### What problem this project solves

Modern teams struggle with:

- Manually created environments
    
- Fragile CI/CD pipelines
    
- Configuration drift
    
- Click-ops in cloud consoles
    
- Unclear ownership boundaries between infra, CI, and apps
    

This project demonstrates a **production-realistic platform** that solves those problems by:

- Treating **environments as code**
    
- Enforcing **clear ownership boundaries**
    
- Eliminating manual steps
    
- Supporting **on-demand environment creation**
    
- Supporting **safe, auditable updates**
    
- Scaling naturally to more teams and services
    
As main author puts it:
> The goal is to be able to demonstrate being able to create new environments programmatically in a single command and hibernate or tear down those environments in a single command too, automating out almost all the dull time-taking processes. I'll be using Pulumi (in Python unfortunately because most dev-ops people can at least sorta digest python), helm, AWS (free tier, goal is for this demo project to not cost me anything or at the very least be extremely cheap), Jenkins and ArgoCD or Flux.

---

### What this project is _not_

- It is not a toy Kubernetes demo
    
- It is not a single-repo “everything lives here” setup
    
- It is not a CI-does-everything pipeline
    
- It is not click-ops driven
    

This is a **platform-level** demonstration, not an application demo.

---

## 2. Core Principles

This system is built around a small number of **explicit, non-negotiable principles**.

### 2.1 Separation of responsibilities

Each layer has _one job_:

|Layer|Responsibility|
|---|---|
|Infrastructure (Pulumi)|What _can exist_|
|GitOps|What _should be running_|
|CI|Build and publish artifacts|
|Controllers|Continuous reconciliation|
|Humans|Declare intent, not mutate state|

No layer performs another layer’s job.

---

### 2.2 Environments are first-class primitives

An **environment** is not a folder, not a convention, and not a manual process.

An environment is a concrete, codified entity defined by:

- A Kubernetes namespace
    
- A DNS subdomain
    
- A set of desired workloads
    
- A set of configuration & secrets
    
- A reconciliation controller
    

Environments are:

- Created programmatically
    
- Reproducible
    
- Disposable
    

---

### 2.3 Declarative, pull-based deployment

- No system pushes changes into the cluster imperatively
    
- No CI job runs `kubectl` or `helm upgrade`
    
- The cluster converges to declared state automatically
    

This is achieved via GitOps.

---

## 3. High-Level Architecture

### Core technologies

- **Amazon Web Services**
    
- **Kubernetes (EKS)**
    
- **Pulumi**
    
- **Flux** or **Argo CD**
    
- **Jenkins**
    
- **Helm**
    
- **Kaniko**
    
- **SOPS** (Git-encrypted secrets)
    

---
## 4. Repository Structure & Ownership

The platform intentionally uses **multiple repositories**, each with a well-defined scope.

---

### 4.1 `infra` repository (platform & capabilities)

**Purpose:**  
Defines _what infrastructure exists_ and _what environments are allowed to run_.

**Owns:**

- VPC, networking
    
- EKS cluster & node groups
    
- IAM & IRSA
    
- Jenkins EC2 or kube service
    
- Flux or Argo CD installation
    
- Kubernetes namespaces
    
- Helm **charts** (templates only)
    
- Flux or Argo CD Application definitions
    

**Does not own:**

- Secrets
    
- Image tags
    
- Runtime configuration
    
- Environment-specific desired state
    

**Change cadence:** rare, deliberate, high-impact

This repository is structured in **layers** (details in section 5), thus defined closely like so:
```
infra/
├─ platform/          # Layer 1 
├─ environments/      # Layer 2
└─ env-addons/        # Layer 3
   ├─ rds/
   │  ├─ Pulumi.yaml
   │  └─ __main__.py
   ├─ redis/
   ├─ s3/
   └─ README.md
```

---

### 4.2 `git-ops` repository (desired state)

**Purpose:**  
Defines _what should be running in each environment_.

**Owns:**

- Helm values per service per environment
    
- Resource sizing (CPU, memory, replicas)
    
- Feature flags
    
- Image references
    
- **Encrypted secrets** (SOPS)
    

**Does not own:**

- AWS resources
    
- Cluster topology
    
- Templates
    
- CI logic
    

**Change cadence:** frequent, safe, reviewable

This repository is the **single source of truth for runtime state**.

---

### 4.3 Application repositories

**Purpose:**  
Define how applications are built.

Each app repo contains:

- Source code
    
- Dockerfile
    
- Jenkinsfile (build pipeline only)
    

App repos:

- Do **not** deploy
    
- Do **not** know about environments
    
- Do **not** know about infrastructure
    

---

## 5. Infrastructure Layer (Pulumi)

Pulumi is used in **layers**, not as a monolith.

---

### 5.1 Platform layer

Run rarely.

Creates:

- Network foundation
    
- EKS cluster
    
- Shared IAM roles
    
- Jenkins EC2 or kube service
    
- Flux or Argo CD installation
    

Once stable, this layer changes infrequently.

---

### 5.2 Environment layer

Run now-and-then.

For each environment, Pulumi:

- Creates a Kubernetes namespace
    
- Creates Flux or Argo CD Application(s)
    
- Wires the environment to GitOps state
    

Pulumi **does not deploy applications** in this layer.  
It only registers environments.

### 5.3 Environment Add-On Layer (Optional, Composable Infrastructure)

Maybe run often.

Not all environments require the same supporting infrastructure.

Some environments may need:

- A database
- An object store
- A cache
- A message queue
- Temporary or experimental infrastructure

This layer exists to support **environment-specific, opt-in infrastructure**, without polluting:

- The global platform layer
- The core environment lifecycle
- The GitOps desired-state model

It allows the platform to remain **stable and generic**, while enabling **controlled flexibility** when needed. Add-ons are applied **explicitly**, never implicitly.

Example:

`cd infra/env-addons/rds pulumi stack select dev pulumi up`

This creates:

- A database for `dev`
- Nothing for `qa` or `prod` unless explicitly run there

This avoids surprise costs, accidental sprawl, and unclear ownership.

---

## 6. GitOps Model (Flux or Argo CD)

Flux and Argo CD are for "watch Git → render manifests → apply → reconcile"

### Responsibilities

- Watches the GitOps repo
    
- Renders Helm charts
    
- Applies manifests to Kubernetes
    
- Continuously reconciles drift
    
- Self-heals manual changes
    

---

### Helm usage model

- Helm **charts** live in `infra`
    
- Helm **values** live in `git-ops`
    
- Flux or Argo CD stitch them together
    

This cleanly separates:

- _How things are deployed_ vs _what is deployed_
    

---

## 7. Secrets & Configuration

### 7.1 Secrets

Secrets are managed via **GitOps-encrypted files**:

- Encrypted with **SOPS**
    
- Committed safely to Git
    
- Decrypted **only inside the cluster**
    
- Never stored in plaintext in repos
    

Kubernetes consumes them as native `Secret` objects.

---

### 7.2 Configuration values

Non-sensitive configuration (replicas, memory, feature flags, image tags) lives in:

- `git-ops/envs/<env>/<service>.yaml`
    

These files are:

- Small
    
- Diffable
    
- Reviewable
    
- Safe for Git
    

---

### 7.3 `.env` developer workflow

- `.env` files are treated as **input artifacts**, not storage
    
- Local `.env` → encrypted → committed
    
- Decryption only happens in-cluster
    

This preserves developer ergonomics while maintaining safety.

---

## 8. CI/CD Pipeline Design

### CI responsibility (Jenkins)

Jenkins is strictly a **build system**.

For each application:

1. Checkout code
    
2. Run tests / lint (optional)
    
3. Build image via Kaniko (in EKS)
    
4. Push image to ECR
    

Jenkins **does not deploy**.

---

### CD responsibility (GitOps)

Deployment happens when:

- GitOps repo changes
    
- Flux or Argo CD detects drift
    
- Cluster converges automatically
    

This cleanly decouples build and deploy.

---

## 9. Environment Lifecycle

### Creating a new environment

This is the defining capability of the platform.

**Flow:**

1. **Define intent**
    
    - Create environment folder in GitOps repo
        
    - Add initial values & encrypted secrets
        
2. **Apply infrastructure**
    
    ```bash
    pulumi up --stack <env>
    ```
    
1. **Flux or Argo CD sync**
    
    - Namespace appears
        
    - Workloads deploy
        

This can be wrapped in one or two commands via Makefile or CLI tooling.

---

### Updating an environment

- Edit GitOps values or secrets
    
- Commit & push
    
- Flux or Argo CD reconcile automatically
    

No manual redeploy commands.

---

### Destroying an environment

- Delete Pulumi stack
    
- Namespace and workloads are removed
    
- No dangling resources
    

---

## 10. Why This Architecture Works

### Strengths

- Clear ownership boundaries
    
- Zero click-ops
    
- Auditable changes
    
- Safe secret handling
    
- Easy environment creation
    
- Scales to more services and teams
    
- Naturally compatible with future tooling
    

---

### Conscious trade-offs

- More repositories
    
- More explicit structure
    
- Slightly higher conceptual overhead
    

These trade-offs are deliberate and aligned with **platform maturity**.

---

## 11. Future Extensions (Supported, Not Required)

This architecture supports, without redesign:

- Observability stacks (LGTM / Prometheus / Grafana)
    
- Per-environment databases
    
- Feature preview environments
    
- Flux or Argo Rollouts
    
- Multi-cluster GitOps
    
- Policy enforcement (OPA / Kyverno)
    

---

## 12. Summary

This project demonstrates:

- Platform-level thinking
    
- Mature CI/CD separation
    
- Correct use of Kubernetes & GitOps
    
- Safe secrets management
    
- Reproducible environment lifecycles
    
- Clear and explainable architecture
    

It is not “clever infrastructure”.  
It is **boring, intentional, and scalable** — which is exactly the point.