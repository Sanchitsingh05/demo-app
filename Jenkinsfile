pipeline {
  agent any
  environment {
    APP_NAME      = "demo"
    DOCKERHUB_USER = "sanchit0305"
    IMAGE          = "${DOCKERHUB_USER}/${APP_NAME}"
    HELM_CHART_DIR = "helm/demo"
    HELM_REPO_GH   = "Sanchitsingh05/helm-charts"
    HELM_REPO_URL  = "https://sanchitsingh05.github.io/helm-charts"  // lower-case safer
  }
  options { timestamps() }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        sh 'git rev-parse --short HEAD > .git/shortsha'
      }
    }

    stage('Docker Build & Push') {
      steps {
        script {
          def SHA = sh(returnStdout: true, script: 'cat .git/shortsha').trim()
          sh """
            docker build -t ${IMAGE}:${SHA} -t ${IMAGE}:latest .
          """
          withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                                           usernameVariable: 'DH_USER',
                                           passwordVariable: 'DH_PASS')]) {
            sh """
              echo "${DH_PASS}" | docker login -u "${DH_USER}" --password-stdin
              docker push ${IMAGE}:${SHA}
              docker push ${IMAGE}:latest
            """
          }
          env.IMAGE_TAG = SHA
        }
      }
    }

    stage('Package & Publish Helm Chart (main only)') {
      when { branch 'main' }
      steps {
        script {
          sh 'helm version && kubectl version --client'
          sh """
            helm lint ${HELM_CHART_DIR} || true
            mkdir -p chart-packages
            helm package ${HELM_CHART_DIR} --version ${BUILD_NUMBER} \
              --app-version ${IMAGE_TAG} -d chart-packages
          """
          env.CHART_TGZ    = sh(returnStdout: true, script: "ls chart-packages/*.tgz").trim()
          env.CHART_VERSION = "${BUILD_NUMBER}"

          withCredentials([string(credentialsId: 'github-token', variable: 'GH_TOKEN')]) {
            sh """
              rm -rf helm-repo && git clone https://github.com/${HELM_REPO_GH}.git helm-repo
              cd helm-repo
              git checkout gh-pages
              cp ../${CHART_TGZ} ./
              if [ -f index.yaml ]; then
                helm repo index . --url ${HELM_REPO_URL} --merge index.yaml
              else
                helm repo index . --url ${HELM_REPO_URL}
              fi
              git add .
              git -c user.name="jenkins-bot" -c user.email="jenkins-bot@local" \
                commit -m "Add chart ${APP_NAME}-${CHART_VERSION}, image ${IMAGE}:${IMAGE_TAG}" || true
              git push https://${GH_TOKEN}@github.com/${HELM_REPO_GH}.git gh-pages
            """
          }
        }
      }
    }

    stage('Deploy to Minikube via Helm (main only)') {
      when { branch 'main' }
      steps {
        script {
          sh """
            helm repo add demo-charts ${HELM_REPO_URL} --force-update
            helm repo update
            kubectl create namespace demo --dry-run=client -o yaml | kubectl apply -f -
            helm upgrade --install demo demo-charts/${APP_NAME} \
              --version ${CHART_VERSION} \
              --namespace demo \
              --set image.repository=${IMAGE} \
              --set image.tag=${IMAGE_TAG} \
              --set service.nodePort=30080 \
              --wait --timeout 120s
          """
        }
      }
    }
  }

  post {
    always {
      sh 'docker logout || true'
      archiveArtifacts artifacts: 'chart-packages/*.tgz', onlyIfSuccessful: false, allowEmptyArchive: true
    }
  }
}
