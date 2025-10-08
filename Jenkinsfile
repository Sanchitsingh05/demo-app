pipeline {
  agent any

  environment {
    // ==== adjust only if your accounts differ ====
    APP_NAME       = "demo"
    DOCKERHUB_USER = "sanchit0305"
    IMAGE          = "${DOCKERHUB_USER}/${APP_NAME}"

    // The source Helm chart is inside this repo
    HELM_CHART_DIR = "helm/demo"

    // GitHub Pages repo that hosts packaged charts + index.yaml
    HELM_REPO_GH   = "Sanchitsingh05/helm-charts"
    HELM_REPO_URL  = "https://sanchitsingh05.github.io/helm-charts"
    // =============================================
  }

  options {
    timestamps()
    // disableConcurrentBuilds() // uncomment if you want to prevent overlapping builds
  }

  stages {

    stage('Checkout') {
      steps {
        checkout scm
        sh 'git rev-parse --short HEAD > .git/shortsha'
      }
    }

    // ---- DEBUG stage you requested ----
    stage('DEBUG show Jenkinsfile & env') {
      steps {
        sh '''
          echo "==== DEBUG: Jenkinsfile being used (first 120 lines) ===="
          sed -n '1,120p' Jenkinsfile || true

          echo "==== DEBUG: Key env values ===="
          echo "HELM_REPO_URL=$HELM_REPO_URL"
          echo "APP_NAME=$APP_NAME"
          echo "IMAGE=$IMAGE"
        '''
      }
    }

    stage('Docker Build & Push') {
      steps {
        script {
          // resolve short SHA and expose to shell as $SHA
          env.SHA = sh(returnStdout: true, script: "cat .git/shortsha").trim()

          // Build and push with only shell expansions
          sh '''
            set -e
            docker build -t "$IMAGE:$SHA" -t "$IMAGE:latest" .
          '''

          withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                                           usernameVariable: 'DH_USER',
                                           passwordVariable: 'DH_PASS')]) {
            sh '''
              set -e
              echo "$DH_PASS" | docker login -u "$DH_USER" --password-stdin
              docker push "$IMAGE:$SHA"
              docker push "$IMAGE:latest"
            '''
          }

          // Publish the image tag for later stages
          env.IMAGE_TAG = env.SHA
        }
      }
    }

    stage('Package & Publish Helm Chart (main only)') {
      when { branch 'main' }
      steps {
        script {
          sh 'helm version && kubectl version --client'

          // Use SemVer for the chart version (export to shell)
          env.CHART_VERSION = "0.1.${env.BUILD_NUMBER}"

          // Package chart to ./chart-packages
          sh '''
            set -e
            helm lint "$HELM_CHART_DIR" || true
            mkdir -p chart-packages
            helm package "$HELM_CHART_DIR" \
              --version "$CHART_VERSION" \
              --app-version "$IMAGE_TAG" \
              -d chart-packages
          '''

          // Find the packaged tgz (expose to shell as $CHART_TGZ)
          env.CHART_TGZ = sh(returnStdout: true, script: "ls chart-packages/*.tgz").trim()

          // Push tgz + index.yaml to gh-pages
          withCredentials([string(credentialsId: 'github-token', variable: 'GH_TOKEN')]) {
            sh '''
              set -e
              rm -rf helm-repo && git clone "https://github.com/$HELM_REPO_GH.git" helm-repo
              cd helm-repo
              git checkout gh-pages || git checkout -b gh-pages

              # Copy freshly packaged chart into Pages worktree
              cp "../$CHART_TGZ" ./

              # Create or merge index.yaml with the public URL
              if [ -f index.yaml ]; then
                helm repo index . --url "$HELM_REPO_URL" --merge index.yaml
              else
                helm repo index . --url "$HELM_REPO_URL"
              fi

              git add .
              git -c user.name="jenkins-bot" -c user.email="jenkins-bot@local" \
                commit -m "Add chart $APP_NAME-$CHART_VERSION, image $IMAGE:$IMAGE_TAG" || true

              git push "https://$GH_TOKEN@github.com/$HELM_REPO_GH.git" gh-pages
            '''
          }
        }
      }
    }

    stage('Deploy to Minikube via Helm (main only)') {
      when { branch 'main' }
      steps {
        script {
          // POSIX-safe wait loop using seq; all $ vars are shell-expanded, not Groovy
          sh '''
            set -e

            # Add/refresh the public chart repo (lowercase URL already in HELM_REPO_URL)
            helm repo add demo-charts "$HELM_REPO_URL" --force-update || true

            # Wait up to ~3 minutes for GitHub Pages to serve the updated index.yaml
            ATTEMPTS=12
            for i in $(seq 1 $ATTEMPTS); do
              helm repo update || true

              # Does the repo show our exact new version?
              if helm search repo "demo-charts/$APP_NAME" -l \
                   | awk 'NR>1{print $2}' \
                   | grep -qx "$CHART_VERSION"; then
                echo "Found $APP_NAME $CHART_VERSION in repo."
                FOUND=yes
                break
              fi

              echo "Chart $APP_NAME $CHART_VERSION not visible yet. Waiting 15s... ($i/$ATTEMPTS)"
              sleep 15
            done

            # Final verification before deploy
            if ! helm search repo "demo-charts/$APP_NAME" -l \
                 | awk 'NR>1{print $2}' | grep -qx "$CHART_VERSION"; then
              echo "ERROR: $APP_NAME $CHART_VERSION still not visible in repo. Check gh-pages & index.yaml"
              exit 1
            fi

            # Ensure namespace exists
            kubectl create namespace demo --dry-run=client -o yaml | kubectl apply -f -

            # Deploy the exact version we just published
            helm upgrade --install demo "demo-charts/$APP_NAME" \
              --version "$CHART_VERSION" \
              --namespace demo \
              --set "image.repository=$IMAGE" \
              --set "image.tag=$IMAGE_TAG" \
              --set "service.nodePort=30080" \
              --wait --timeout 120s
          '''
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
