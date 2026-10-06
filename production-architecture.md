# Production architecture (diagram for slides)

## Runtime

```mermaid
flowchart LR
    user([User's browser])
    friend([Friend with a share link])

    subgraph edge[Edge]
        r53[Route 53<br/>domain]
        cf[CloudFront<br/>HTTPS]
        waf[AWS WAF<br/>rate limits, managed rules]
    end

    subgraph auth[Sign-in]
        cognito[Amazon Cognito<br/>OAuth 2.0 / OIDC, MFA]
    end

    subgraph app[Application]
        apigw[API Gateway<br/>HTTP API + JWT authorizer]
        fn[Lambda<br/>signs links, serves share links]
        ddb[(DynamoDB<br/>owner, expiry, revoked,<br/>download count)]
    end

    subgraph storage[Storage]
        site[(S3 site bucket<br/>web page)]
        files[(S3 upload bucket<br/>KMS encrypted, private)]
        scan[GuardDuty<br/>malware scan]
    end

    subgraph ops[Operations]
        cw[CloudWatch<br/>logs, alarms]
        budgets[AWS Budgets<br/>cost alerts]
    end

    user --> r53 --> waf --> cf
    cf -->|web page| site
    user -->|1. sign in| cognito
    cognito -->|2. JWT token| user
    user -->|3. request links + token| apigw
    apigw -->|valid token only| fn
    fn <-->|file records| ddb
    fn -->|4. signed upload link| user
    user -->|5. upload file directly| files
    files --> scan
    friend -->|share link| apigw
    fn -->|checks record, redirects to signed download| friend
    fn --> cw
    apigw --> cw
    budgets -.-> cw
```

## Delivery pipeline

```mermaid
flowchart LR
    dev([Developer]) -->|pull request| git[GitHub<br/>reviews required]
    git -->|merge to main| ci[GitHub Actions<br/>or CodePipeline + CodeBuild]

    subgraph pipeline[Pipeline stages]
        direction LR
        test[Lint and<br/>unit tests] --> build[sam build<br/>or cdk synth]
        build --> devdeploy[Deploy to dev]
        devdeploy --> smoke[Smoke test]
        smoke --> approve{Manual<br/>approval}
        approve --> proddeploy[Deploy to prod<br/>canary, auto rollback]
    end

    ci --> test

    oidc[[OIDC role<br/>no stored access keys]] -.-> ci

    subgraph accounts[Separate AWS accounts]
        devacct[(Dev account)]
        prodacct[(Prod account)]
    end

    devdeploy --> devacct
    proddeploy --> prodacct

    sso[IAM Identity Center<br/>people use SSO, never root] -.-> accounts
```

## What each part fixes compared with the demo

| Demo | Production |
|---|---|
| Anyone can call the Function URL | API Gateway + Cognito: only signed-in users reach the Lambda |
| No record of files | DynamoDB: owner, revoke a link, limit downloads |
| `*.lambda-url...` and `*.cloudfront.net` addresses | Route 53 domain with HTTPS |
| No abuse protection | WAF rate limits and managed rules |
| Click-through console deploys | Pipeline, infrastructure as code, dev and prod kept apart |
| Long-lived access keys on a laptop | OIDC and SSO, temporary credentials only |
