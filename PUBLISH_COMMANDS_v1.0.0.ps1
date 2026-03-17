$GitHubUser = "bleakM"
$RepoName = "VoteFree"

if ([string]::IsNullOrWhiteSpace($GitHubUser) -or [string]::IsNullOrWhiteSpace($RepoName)) {
    Write-Error "Please set GitHub user and repo name first."
    exit 1
}

git init
git add .
git commit -m "chore: initial open-source release v1.0.0"
git branch -M main
git remote remove origin 2>$null
git remote add origin "https://github.com/$GitHubUser/$RepoName.git"
git push -u origin main

git tag v1.0.0
git push origin v1.0.0

Write-Host 'Done. Source and tag pushed. Next: create GitHub Release and upload zip files.'
