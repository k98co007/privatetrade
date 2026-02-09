pipeline {
    agent any

    environment {
        REGISTRY = 'docker.io'
        IMAGE_NAME = 'privatetrade/backtesting-simulator'
        DOCKER_CREDENTIALS = credentials('docker-hub-credentials')
        SLACK_WEBHOOK = credentials('slack-webhook-url')
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '30'))
        timestamps()
        timeout(time: 1, unit: 'HOURS')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.BUILD_INFO = """
                        Build: ${BUILD_NUMBER}
                        Branch: ${BRANCH_NAME}
                        Commit: ${GIT_COMMIT.take(8)}
                        Author: ${GIT_COMMITTER_NAME}
                    """
                }
            }
        }

        stage('Build & Lint') {
            steps {
                script {
                    sh '''
                        echo "Building project..."
                        npm ci
                        npm run build
                        npm run lint
                    '''
                }
            }
        }

        stage('Unit Tests') {
            steps {
                script {
                    sh '''
                        echo "Running unit tests..."
                        npm run test:unit -- --coverage
                    '''
                }
                publishHTML([
                    reportDir: 'coverage',
                    reportFiles: 'index.html',
                    reportName: 'Coverage Report'
                ])
            }
        }

        stage('Integration Tests') {
            steps {
                script {
                    sh '''
                        echo "Running integration tests..."
                        npm run test:integration
                    '''
                }
            }
        }

        stage('Security Scan') {
            steps {
                script {
                    sh '''
                        echo "Running security scan..."
                        npm audit --audit-level=moderate || true
                    '''
                }
            }
        }

        stage('Build Docker Image') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                    tag pattern: "v\\d+\\.\\d+\\.\\d+", comparator: "REGEXP"
                }
            }
            steps {
                script {
                    sh '''
                        echo "Building Docker image..."
                        docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} .
                        docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${IMAGE_NAME}:latest
                        
                        echo "Pushing to Docker Hub..."
                        echo ${DOCKER_CREDENTIALS_PSW} | docker login -u ${DOCKER_CREDENTIALS_USR} --password-stdin
                        docker push ${IMAGE_NAME}:${BUILD_NUMBER}
                        docker push ${IMAGE_NAME}:latest
                    '''
                }
            }
        }

        stage('Deploy to Staging') {
            when {
                branch 'develop'
            }
            environment {
                TARGET_ENV = 'staging'
            }
            steps {
                script {
                    sh '''
                        echo "Deploying to staging..."
                        docker-compose -f docker-compose-staging.yml down
                        docker-compose -f docker-compose-staging.yml up -d
                        
                        # Wait for health check
                        sleep 5
                        for i in {1..30}; do
                            if curl -f http://localhost:3000/api/health; then
                                echo "✅ Staging deployment successful"
                                exit 0
                            fi
                            sleep 2
                        done
                        exit 1
                    '''
                }
            }
            post {
                failure {
                    sh '''
                        curl -X POST ${SLACK_WEBHOOK} \
                            -d '{"text": "❌ Staging deployment failed"}'
                    '''
                }
            }
        }

        stage('Deploy to Production') {
            when {
                tag pattern: "v\\d+\\.\\d+\\.\\d+", comparator: "REGEXP"
            }
            environment {
                TARGET_ENV = 'production'
            }
            input {
                message "Deploy to production?"
                ok "Deploy"
            }
            steps {
                script {
                    sh '''
                        echo "Deploying to production (Blue-Green)..."
                        VERSION=${TAG_NAME}
                        
                        # Blue-Green deployment
                        bash scripts/deploy-blue-green.sh ${VERSION}
                    '''
                }
            }
            post {
                success {
                    sh '''
                        curl -X POST ${SLACK_WEBHOOK} \
                            -d '{"text": "✅ Production deployment successful"}'
                    '''
                }
                failure {
                    sh '''
                        curl -X POST ${SLACK_WEBHOOK} \
                            -d '{"text": "❌ Production deployment failed. Rolling back."}'
                        bash scripts/rollback.sh
                    '''
                }
            }
        }
    }

    post {
        always {
            cleanWs()
            junit 'test-results/*.xml'
        }
        failure {
            emailext(
                subject: "Build #${BUILD_NUMBER} Failed",
                body: "${BUILD_INFO}",
                to: "${CHANGE_AUTHOR_EMAIL}"
            )
        }
    }
}
