import * as cdk from "aws-cdk-lib";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as ecr from "aws-cdk-lib/aws-ecr";
import * as iam from "aws-cdk-lib/aws-iam";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import { Construct } from "constructs";

interface FoundationStackProps extends cdk.StackProps {
  readonly githubOidcSubject: string;
}

export class FoundationStack extends cdk.Stack {
  public readonly repository: ecr.IRepository;
  public readonly mediaBucket: s3.IBucket;
  public readonly mediaDomainName: string;
  public readonly runtimeSecret: secretsmanager.ISecret;

  public constructor(
    scope: Construct,
    id: string,
    props: FoundationStackProps,
  ) {
    super(scope, id, props);

    const account = cdk.Stack.of(this).account;
    const region = cdk.Stack.of(this).region;

    const repository = new ecr.Repository(this, "Repository", {
      repositoryName: "genvilla-blog",
      imageScanOnPush: true,
      imageTagMutability: ecr.TagMutability.IMMUTABLE,
      encryption: ecr.RepositoryEncryption.AES_256,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      emptyOnDelete: false,
    });
    repository.addLifecycleRule({
      description: "Keep the 25 newest production images",
      maxImageCount: 25,
      rulePriority: 1,
    });
    this.repository = repository;

    const mediaBucket = new s3.Bucket(this, "MediaBucket", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      versioned: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });
    this.mediaBucket = mediaBucket;

    const mediaDistribution = new cloudfront.Distribution(
      this,
      "MediaDistribution",
      {
        defaultBehavior: {
          origin: origins.S3BucketOrigin.withOriginAccessControl(mediaBucket),
          viewerProtocolPolicy:
            cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
          cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
          responseHeadersPolicy:
            cloudfront.ResponseHeadersPolicy.SECURITY_HEADERS,
          compress: true,
        },
      },
    );
    this.mediaDomainName = mediaDistribution.distributionDomainName;

    const runtimeSecret = new secretsmanager.Secret(this, "RuntimeSecret", {
      secretName: "genvilla-blog/runtime",
      description:
        "Django, MongoDB, Cloudinary, and email credentials for the production blog",
      generateSecretString: {
        secretStringTemplate: JSON.stringify({}),
        generateStringKey: "DJANGO_SECRET_KEY",
        passwordLength: 64,
        excludePunctuation: true,
      },
    });
    this.runtimeSecret = runtimeSecret;

    const oidcProvider = iam.OpenIdConnectProvider.fromOpenIdConnectProviderArn(
      this,
      "GitHubOidcProvider",
      `arn:${cdk.Aws.PARTITION}:iam::${account}:oidc-provider/token.actions.githubusercontent.com`,
    );
    const deployRole = new iam.Role(this, "GitHubDeployRole", {
      roleName: "genvilla-blog-github-prod-deploy",
      description:
        "Deploys the GenVilla blog through the production GitHub environment",
      assumedBy: new iam.WebIdentityPrincipal(
        oidcProvider.openIdConnectProviderArn,
        {
          StringEquals: {
            "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
            "token.actions.githubusercontent.com:sub": props.githubOidcSubject,
          },
        },
      ),
      maxSessionDuration: cdk.Duration.hours(1),
    });

    repository.grantPullPush(deployRole);
    deployRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "InspectDeploymentImages",
        actions: ["ecr:DescribeImages"],
        resources: [repository.repositoryArn],
      }),
    );
    deployRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "AssumeCdkBootstrapRoles",
        actions: ["sts:AssumeRole"],
        resources: [
          `arn:${cdk.Aws.PARTITION}:iam::${account}:role/cdk-hnb659fds-*-${account}-${region}`,
        ],
      }),
    );
    deployRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "ReadCdkDeploymentState",
        actions: [
          "cloudformation:DescribeStackEvents",
          "cloudformation:DescribeStacks",
          "cloudformation:GetTemplate",
          "ssm:GetParameter",
        ],
        resources: ["*"],
      }),
    );

    new cdk.CfnOutput(this, "RepositoryUri", {
      value: repository.repositoryUri,
    });
    new cdk.CfnOutput(this, "MediaBucketName", {
      value: mediaBucket.bucketName,
    });
    new cdk.CfnOutput(this, "MediaUrl", {
      value: `https://${mediaDistribution.distributionDomainName}`,
    });
    new cdk.CfnOutput(this, "GitHubDeployRoleArn", {
      value: deployRole.roleArn,
    });
  }
}
