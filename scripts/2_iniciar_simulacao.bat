@echo off
setlocal enabledelayedexpansion

REM Define os diretorios de mundos do projeto
set "WORLDS_DIR=%~dp0..\src\articubot_one\worlds"
set "ROOT_WORLDS_DIR=%~dp0..\worlds"

REM Garante que a pasta worlds na raiz exista
if not exist "!ROOT_WORLDS_DIR!" mkdir "!ROOT_WORLDS_DIR!" >nul 2>&1

REM Converte arquivos sem extensao salvos pelo Gazebo na pasta worlds para .world
if exist "!ROOT_WORLDS_DIR!" (
    for /f "delims=" %%G in ('dir /b /a-d "!ROOT_WORLDS_DIR!" 2^>nul') do (
        if "%%~xG"=="" (
            if not exist "!ROOT_WORLDS_DIR!\%%G.world" (
                copy /y "!ROOT_WORLDS_DIR!\%%G" "!ROOT_WORLDS_DIR!\%%G.world" >nul 2>&1
            )
        )
    )
)
if exist "!WORLDS_DIR!" (
    for /f "delims=" %%G in ('dir /b /a-d "!WORLDS_DIR!" 2^>nul') do (
        if "%%~xG"=="" (
            if not exist "!WORLDS_DIR!\%%G.world" (
                copy /y "!WORLDS_DIR!\%%G" "!WORLDS_DIR!\%%G.world" >nul 2>&1
            )
        )
    )
)

REM Sincroniza arquivos .world entre a raiz worlds e src/articubot_one/worlds
if exist "!ROOT_WORLDS_DIR!" if exist "!WORLDS_DIR!" (
    copy /y "!ROOT_WORLDS_DIR!\*.world" "!WORLDS_DIR!\" >nul 2>&1
    copy /y "!WORLDS_DIR!\*.world" "!ROOT_WORLDS_DIR!\" >nul 2>&1
)

if not exist "!WORLDS_DIR!" (
    if exist "!ROOT_WORLDS_DIR!" (
        set "WORLDS_DIR=!ROOT_WORLDS_DIR!"
    ) else (
        echo [ERRO] Nao foi possivel encontrar a pasta de mundos do Gazebo.
        pause
        exit /b 1
    )
)

:MENU_MUNDOS
cls
echo ======================================================================
echo             ESCOLHA O MUNDO PARA A SIMULACAO DO GAZEBO
echo ======================================================================
echo.
echo   Mundos disponiveis na pasta worlds:
echo.

set count=0
set "DEFAULT_INDEX=1"

REM 1. Coloca a pista oficial circuit1.world como primeira opcao
if exist "%WORLDS_DIR%\circuit1.world" (
    set /a count+=1
    set "WORLD_!count!=circuit1.world"
    echo     [!count!] circuit1.world  ^(Pista Oficial Completa - Recomendada^)
)

REM 2. Lista os demais mundos dinamicamente
for /f "delims=" %%F in ('dir /b /a-d "%WORLDS_DIR%\*.world" 2^>nul') do (
    if /i not "%%F"=="circuit1.world" (
        set /a count+=1
        set "WORLD_!count!=%%F"
        if /i "%%F"=="circle_world.world" (
            echo     [!count!] %%F  ^(Pista Circular - 4 Curvas^)
        ) else (
            echo     [!count!] %%F
        )
    )
)

if !count! equ 0 (
    echo   [AVISO] Nenhum arquivo .world encontrado na pasta worlds.
    echo.
    echo   Pressione qualquer tecla para voltar...
    pause >nul
    exit /b 1
)

echo.
echo     [0] Cancelar e voltar ao menu
echo.
echo ======================================================================

:PEDIR_ESCOLHA
set "ESCOLHA="
set /p "ESCOLHA= Digite o numero do mundo que deseja carregar [1-!count!] (Padrao: !DEFAULT_INDEX!): "

REM Remove espacos acidentais
if defined ESCOLHA set "ESCOLHA=!ESCOLHA: =!"

REM Se pressionar Enter sem digitar nada, assume o padrão
if "!ESCOLHA!"=="" set "ESCOLHA=!DEFAULT_INDEX!"

REM Opção de cancelar
if "!ESCOLHA!"=="0" (
    echo.
    echo  Operacao cancelada. Retornando ao menu...
    ping -n 2 127.0.0.1 >nul
    exit /b 0
)

REM Validação numérica
set "VALIDO=0"
for /l %%i in (1,1,!count!) do (
    if "!ESCOLHA!"=="%%i" set "VALIDO=1"
)

if "!VALIDO!"=="0" (
    echo.
    echo   [ERRO] Opcao invalida: "!ESCOLHA!". Escolha entre 1 e !count! ^(ou 0 para cancelar^).
    echo.
    goto PEDIR_ESCOLHA
)

set "MUNDO_ESCOLHIDO=!WORLD_%ESCOLHA%!"

echo.
echo ======================================================================
echo  Iniciando SIMULACAO COMPLETA no Gazebo...
echo  Mundo selecionado: !MUNDO_ESCOLHIDO!
echo ======================================================================
echo.

wsl -d Ubuntu-24.04 docker start meu_container_ros >nul 2>&1
start "Simulacao AGV - Gazebo (!MUNDO_ESCOLHIDO!)" cmd /k "wsl -d Ubuntu-24.04 docker exec -it meu_container_ros /workspace/scripts/ros_exec.sh ros2 launch agv_hardware agv_complete.launch.py sim_mode:=true world:=!MUNDO_ESCOLHIDO!"

exit /b 0
