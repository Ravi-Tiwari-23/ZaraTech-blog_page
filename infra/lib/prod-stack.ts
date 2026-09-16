import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecr from "aws-cdk-lib/aws-ecr";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as elbv2 from "aws-cdk-lib/aws-elasticloadbalancingv2";
import * as logs from "aws-cdk-lib/aws-logs";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import { Construct } from "constructs";

interface ProdStackProps extends cdk.StackProps {
  readonly repository: ecr.IRepository;
  readonly runtimeSecret: secretsmanager.ISecret;
  readonly imageTag: string;
  readonly domainName: string;
  readonly clusterName: string;
  readonly albSecurityGroupId: string;
  readonly httpsListenerArn: string;
  readonly certificateArn: string;
}

export class ProdStack extends cdk.Stack {
  public constructor(scope: Construct, id: string, props: ProdStackProps) {
    super(scope, id, props);

    const vpc = ec2.Vpc.fromLookup(this, "Vpc", { isDefault: true });
    const workloadSubnets: ec2.SubnetSelection = {
      subnetType: ec2.SubnetType.PUBLIC,
      availabilityZones: [`${this.region}b`, `${this.region}c`],
    };
    const cluster = ecs.Cluster.fromClusterAttributes(this, "Cluster", {
      clusterName: props.clusterName,
      vpc,
      securityGroups: [],
    });
    const albSecurityGroup = ec2.SecurityGroup.fromSecurityGroupId(
      this,
      "AlbSecurityGroup",
      props.albSecurityGroupId,
      { mutable: false },
    );

    const taskSecurityGroup = new ec2.SecurityGroup(this, "TaskSecurityGroup", {
      vpc,
      description: "Blog accepts traffic only from the shared ALB",
      allowAllOutbound: true,
    });
    taskSecurityGroup.addIngressRule(
      albSecurityGroup,
      ec2.Port.tcp(8000),
      "Blog traffic from the shared ALB",
    );

    const taskDefinition = new ecs.FargateTaskDefinition(
      this,
      "TaskDefinition",
      {
        family: "genvilla-blog-prod",
        cpu: 256,
        memoryLimitMiB: 512,
        runtimePlatform: {
          cpuArchitecture: ecs.CpuArchitecture.ARM64,
          operatingSystemFamily: ecs.OperatingSystemFamily.LINUX,
        },
      },
    );
    const logGroup = new logs.LogGroup(this, "BlogLogs", {
      logGroupName: "/ecs/genvilla-prod/blog",
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });
    const image = ecs.ContainerImage.fromEcrRepository(
      props.repository,
      props.imageTag,
    );
    const environment = {
      DJANGO_DEBUG: "False",
      DJANGO_SETTINGS_MODULE: "blog_main.settings_mongo",
      DJANGO_ALLOWED_HOSTS: props.domainName,
      DJANGO_CSRF_TRUSTED_ORIGINS: `https://${props.domainName}`,
      SEO_BASE_URL: `https://${props.domainName}`,
      AWS_REGION: this.region,
      RELEASE_ID: props.imageTag,
    };
    const secrets = {
      DJANGO_SECRET_KEY: ecs.Secret.fromSecretsManager(
        props.runtimeSecret,
        "DJANGO_SECRET_KEY",
      ),
      MONGODB_URI: ecs.Secret.fromSecretsManager(
        props.runtimeSecret,
        "MONGODB_URI",
      ),
      MONGODB_NAME: ecs.Secret.fromSecretsManager(
        props.runtimeSecret,
        "MONGODB_NAME",
      ),
      CLOUDINARY_CLOUD_NAME: ecs.Secret.fromSecretsManager(
        props.runtimeSecret,
        "CLOUDINARY_CLOUD_NAME",
      ),
      CLOUDINARY_API_KEY: ecs.Secret.fromSecretsManager(
        props.runtimeSecret,
        "CLOUDINARY_API_KEY",
      ),
      CLOUDINARY_API_SECRET: ecs.Secret.fromSecretsManager(
        props.runtimeSecret,
        "CLOUDINARY_API_SECRET",
      ),
      EMAIL_HOST_PASSWORD: ecs.Secret.fromSecretsManager(
        props.runtimeSecret,
        "EMAIL_HOST_PASSWORD",
      ),
      EMAIL_HOST: ecs.Secret.fromSecretsManager(
        props.runtimeSecret,
        "EMAIL_HOST",
      ),
      EMAIL_PORT: ecs.Secret.fromSecretsManager(
        props.runtimeSecret,
        "EMAIL_PORT",
      ),
      EMAIL_HOST_USER: ecs.Secret.fromSecretsManager(
        props.runtimeSecret,
        "EMAIL_HOST_USER",
      ),
      EMAIL_USE_TLS: ecs.Secret.fromSecretsManager(
        props.runtimeSecret,
        "EMAIL_USE_TLS",
      ),
      DEFAULT_FROM_EMAIL: ecs.Secret.fromSecretsManager(
        props.runtimeSecret,
        "DEFAULT_FROM_EMAIL",
      ),
      RESEND_API_KEY: ecs.Secret.fromSecretsManager(
        props.runtimeSecret,
        "RESEND_API_KEY",
      ),
    };

    const migration = taskDefinition.addContainer("Migration", {
      containerName: "migration",
      image,
      command: ["python", "manage.py", "migrate", "--noinput"],
      essential: false,
      environment,
      secrets,
      logging: ecs.LogDrivers.awsLogs({
        logGroup,
        streamPrefix: "migration",
        mode: ecs.AwsLogDriverMode.BLOCKING,
      }),
    });

    const container = taskDefinition.addContainer("Web", {
      containerName: "web",
      image,
      environment,
      secrets,
      logging: ecs.LogDrivers.awsLogs({
        logGroup,
        streamPrefix: "web",
        mode: ecs.AwsLogDriverMode.BLOCKING,
      }),
      stopTimeout: cdk.Duration.seconds(30),
      healthCheck: {
        command: [
          "CMD-SHELL",
          "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz/', timeout=4)\"",
        ],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        retries: 3,
        startPeriod: cdk.Duration.seconds(30),
      },
    });
    container.addContainerDependencies({
      container: migration,
      condition: ecs.ContainerDependencyCondition.SUCCESS,
    });
    container.addPortMappings({
      containerPort: 8000,
      protocol: ecs.Protocol.TCP,
    });

    const service = new ecs.FargateService(this, "Service", {
      cluster,
      serviceName: "genvilla-blog-prod",
      taskDefinition,
      desiredCount: 1,
      assignPublicIp: true,
      vpcSubnets: workloadSubnets,
      securityGroups: [taskSecurityGroup],
      platformVersion: ecs.FargatePlatformVersion.LATEST,
      minHealthyPercent: 100,
      maxHealthyPercent: 200,
      healthCheckGracePeriod: cdk.Duration.seconds(120),
      circuitBreaker: { rollback: true },
    });

    service
      .autoScaleTaskCount({ minCapacity: 1, maxCapacity: 4 })
      .scaleOnCpuUtilization("CpuScaling", {
        targetUtilizationPercent: 70,
        scaleInCooldown: cdk.Duration.minutes(5),
        scaleOutCooldown: cdk.Duration.minutes(1),
      });

    new elbv2.CfnListenerCertificate(this, "ListenerCertificate", {
      listenerArn: props.httpsListenerArn,
      certificates: [{ certificateArn: props.certificateArn }],
    });
    const targetGroup = new elbv2.ApplicationTargetGroup(this, "TargetGroup", {
      vpc,
      port: 8000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targetType: elbv2.TargetType.IP,
      targets: [service],
      deregistrationDelay: cdk.Duration.seconds(30),
      healthCheck: {
        path: "/healthz/",
        healthyHttpCodes: "200",
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        healthyThresholdCount: 2,
        unhealthyThresholdCount: 2,
      },
    });
    const hostRule = new elbv2.CfnListenerRule(this, "HostRule", {
      listenerArn: props.httpsListenerArn,
      priority: 30,
      conditions: [
        {
          field: "host-header",
          hostHeaderConfig: { values: [props.domainName] },
        },
      ],
      actions: [
        {
          type: "forward",
          targetGroupArn: targetGroup.targetGroupArn,
        },
      ],
    });
    service.node.addDependency(hostRule);

    new cdk.CfnOutput(this, "BlogUrl", {
      value: `https://${props.domainName}`,
    });
    new cdk.CfnOutput(this, "ClusterName", {
      value: props.clusterName,
    });
    new cdk.CfnOutput(this, "ServiceName", {
      value: service.serviceName,
    });
  }
}
