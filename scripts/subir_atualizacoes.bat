@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0.."
title Subir Atualizacoes para o GitHub

echo ======================================================================
echo          ENVIAR ATUALIZACOES PARA O GITHUB (GIT ADD + COMMIT + PUSH)
echo ======================================================================
echo.

:: 1. Exibir status atual dos arquivos modificados
echo [1/4] Verificando arquivos modificados no repositorio...
git status -s
echo.

:: 2. Solicitar mensagem do commit
set "MSG="
set /p "MSG=Digite a mensagem do commit (ou ENTER para mensagem padrao): "
if "!MSG!"=="" (
    for /f "tokens=1-4 delims=/ " %%a in ('date /t') do set "DATA_HOJE=%%a-%%b-%%c"
    for /f "tokens=1-2 delims=: " %%a in ('time /t') do set "HORA_HOJE=%%a:%%b"
    set "MSG=Atualizacao do projeto AGV (!DATA_HOJE! !HORA_HOJE!)"
)

echo.
echo Mensagem do commit: "!MSG!"
echo.

:: 3. Adicionar arquivos ao Git
echo [2/4] Adicionando arquivos (git add -A)...
git add -A
if errorlevel 1 (
    echo [ERRO] Falha ao adicionar arquivos ao Git.
    pause
    exit /b 1
)

:: 4. Realizar o commit
echo [3/4] Gravando alteracoes locais (git commit)...
git commit -m "!MSG!"
if errorlevel 1 (
    echo.
    echo [INFO] Nenhuma alteracao pendente para commit ou erro no git commit.
)

:: 5. Enviar para o GitHub
echo.
echo [4/4] Enviando alteracoes para o GitHub (git push origin main)...
git push origin main
if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao enviar para o GitHub.
    echo Verifique sua conexao com a internet ou credenciais do Git.
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo   ATUALIZACOES ENVIADAS PARA O GITHUB COM SUCESSO!
echo ======================================================================
echo.
pause
