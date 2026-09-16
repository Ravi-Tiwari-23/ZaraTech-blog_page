#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { FoundationStack } from "../lib/foundation-stack.js";
import { ProdStack } from "../lib/prod-stack.js";

function requiredContext(app: cdk.App, key: string): string {
  const value: unknown = app.node.tryGetContext(key);
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`Missing required CDK context value: ${key}`);
  }
  return value;
}

const app = new cdk.App();
const account = requiredContext(app, "genvilla-blog:account");
const region = requiredContext(app, "genvilla-blog:region");
const env = { account, region };

const foundation = new FoundationStack(app, "GenvillaBlogFoundation", {
  env,
  stackName: "GenvillaBlogFoundation",
  githubOidcSubject: requiredContext(app, "genvilla-blog:githubOidcSubject"),
  terminationProtection: true,
});

const prod = new ProdStack(app, "GenvillaBlogProd", {
  env,
  stackName: "GenvillaBlogProd",
  repository: foundation.repository,
  runtimeSecret: foundation.runtimeSecret,
  imageTag: requiredContext(app, "genvilla-blog:imageTag"),
  domainName: requiredContext(app, "genvilla-blog:domain"),
  clusterName: requiredContext(app, "genvilla-blog:clusterName"),
  albSecurityGroupId: requiredContext(app, "genvilla-blog:albSecurityGroupId"),
  httpsListenerArn: requiredContext(app, "genvilla-blog:httpsListenerArn"),
  certificateArn: requiredContext(app, "genvilla-blog:certificateArn"),
  terminationProtection: true,
});

prod.addStackDependency(
  foundation,
  "The production service uses the blog repository and runtime secret",
);

cdk.Tags.of(app).add("Project", "genvilla-blog");
cdk.Tags.of(app).add("Environment", "production");
cdk.Tags.of(app).add("ManagedBy", "aws-cdk");
