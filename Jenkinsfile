pipeline {
  agent any
  environment {
    // ==== adjust these to your accounts if different ====
    APP_NAME       = "demo"
    DOCKERHUB_USER = "sanchit0305"
    IMAGE          = "${DOCKERHUB_USER}/${APP_NAME}"

    // chart source lives in this repo (your app repo)
    HELM_CHART_DIR = "helm/demo"

    // GitHub Pages repo that hosts packaged charts + index.yaml
    HELM_REPO_GH   = "Sanchitsingh05/helm-charts"
    HELM_REPO_URL  = "https://sanchitsingh05.github.io/helm-charts"
    // ====================================================
  }
  options {
    timestamps()
    // optional: avoid overlapping deploys
    // disableConcurrentBuilds()
  }

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
            set -e
            docker build -t ${IMAGE}:${SHA} -t ${IMAGE}:latest .
          """

          withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                                           usernameVariable: 'DH_USER',
                                           passwordVariable: 'DH_PASS')]) {
            sh """
              set -e
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

          // --- Use SemVer for the chart version ---
          env.CHART_VERSION = "0.1.${BUILD_NUMBER}"

          sh """
            set -e
            helm lint ${HELM_CHART_DIR} || true
            mkdir -p chart-packages
            helm package ${HELM_CHART_DIR} \
              --version ${CHART_VERSION} \
              --app-version ${IMAGE_TAG} \
              -d chart-packages
          """

          env.CHART_TGZ = sh(returnStdout: true, script: "ls chart-packages/*.tgz").trim()

          withCredentials([string(credentialsId: 'github-token', variable: 'GH_TOKEN')]) {
            sh """
              set -e
              rm -rf helm-repo && git clone https://github.com/${HELM_REPO_GH}.git helm-repo
              cd helm-repo
              git checkout gh-pages || git checkout -b gh-pages

              # Copy the freshly packaged chart into the Pages worktree
              cp ../${CHART_TGZ} ./

              # Build or merge index.yaml with the public URL
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
            set -e

            # Keep repo URL lowercase for safety
            helm repo add demo-charts ${HELM_REPO_URL} --force-update || true

            # Wait up to ~3 minutes for GitHub Pages to serve updated index.yaml
            ATTEMPTS=12
            for i in \$(seq 1 \${ATTEMPTS}); do
              helm repo update || true
              if helm search repo demo-charts/${APP_NAME} -l \\
                   | awk 'NR>1{print \$2}' \\
                   | grep -qx ${CHART_VERSION}; then
                echo "Found ${APP_NAME} ${CHART_VERSION} in repo."
                FOUND=yes
                break
              fi
              echo "Chart ${APP_NAME} ${CHART_VERSION} not visible yet. Waiting 15s... (\$i/\${ATTEMPTS})"
              sleep 15
            done

            # Verify FOUND or bail cleanly
            if ! helm search repo demo-charts/${APP_NAME} -l \\
                 | awk 'NR>1{print \$2}' | grep -qx ${CHART_VERSION}; then
              echo "ERROR: ${APP_NAME} ${CHART_VERSION} still not visible in repo. Check gh-pages & index.yaml"
              exit 1
            fi

            # Ensure namespace exists
            kubectl create namespace demo --dry-run=client -o yaml | kubectl apply -f -

            # Deploy the exact version we just published
            helm upgrade --install demo demo-charts/${APP_NAME} \\
              --version ${CHART_VERSION} \\
              --namespace demo \\
              --set image.repository=${IMAGE} \\
              --set image.tag=${IMAGE_TAG} \\
              --set service.nodePort=30080 \\
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
