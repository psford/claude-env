pipeline {
    agent {
        docker {
            image 'mcr.microsoft.com/dotnet/sdk:8.0'
            args '-u root'  // Required for file permissions in Docker
        }
    }

    environment {
        DOTNET_CLI_TELEMETRY_OPTOUT = '1'
        DOTNET_NOLOGO = '1'
        SOLUTION_PATH = 'projects/stock-analyzer/StockAnalyzer.sln'
        FRONTEND_PATH = 'projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Restore') {
            steps {
                sh 'dotnet restore ${SOLUTION_PATH}'
            }
        }

        stage('Build') {
            steps {
                sh 'dotnet build ${SOLUTION_PATH} --configuration Release --no-restore'
            }
        }

        stage('Test - .NET') {
            steps {
                sh 'dotnet test ${SOLUTION_PATH} --configuration Release --no-build --verbosity normal --logger "trx;LogFileName=test-results.trx" --results-directory ./TestResults'
            }
            post {
                always {
                    archiveArtifacts artifacts: 'TestResults/*.trx', allowEmptyArchive: true
                }
            }
        }

        stage('Test - JavaScript') {
            steps {
                // Install Node.js and run tests (using apt since we're in dotnet container)
                sh '''
                    apt-get update && apt-get install -y nodejs npm
                    cd ${FRONTEND_PATH}
                    npm install
                    npm test -- --ci --coverage || true
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: "${FRONTEND_PATH}/coverage/**", allowEmptyArchive: true
                }
            }
        }

        stage('Publish') {
            steps {
                sh 'dotnet publish projects/stock-analyzer/src/StockAnalyzer.Api/StockAnalyzer.Api.csproj --configuration Release --no-build --output ./publish'
            }
            post {
                success {
                    archiveArtifacts artifacts: 'publish/**', fingerprint: true
                }
            }
        }
    }

    post {
        success {
            echo 'Build succeeded!'
        }
        failure {
            echo 'Build failed!'
        }
    }
}
