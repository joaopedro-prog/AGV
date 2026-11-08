#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_clean_diagrams.py
-----------------------
Gera os arquivos de diagrama eletrico do circuito de potencia do AGV:
 1) docs/hardware/circuito_potencia_agv.drawio (Formato XML compativel com Diagrams.net / Draw.io)
 2) docs/hardware/circuito_potencia_agv.svg (Vetor SVG com estilizacao profissional)
"""

import os
import xml.etree.ElementTree as ET

def get_drawio_xml():
    xml = '''<mxfile host="app.diagrams.net" modified="2026-11-08T19:30:00.000Z" agent="Antigravity AGV Engineering" version="22.1.0" type="device">
  <diagram id="agv_power_circuit" name="Circuito de Potencia AGV">
    <mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1600" pageHeight="1000" background="#FFFFFF" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />

        <!-- TITULO E CABECALHO -->
        <mxCell id="title_box" value="&lt;b style=&quot;font-size: 20px;&quot;&gt;DIAGRAMA ELETRICO DO CIRCUITO DE POTENCIA - AGV AUTONOMO&lt;/b&gt;&lt;br&gt;&lt;span style=&quot;font-size: 13px; color: #475467;&quot;&gt;Tensao Nominal: 12V DC | Bateria MK ES17-12 (18 Ah) | Arquitetura Segura Fail-Safe ISO 13849 / NR-12&lt;/span&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F8F9FA;strokeColor=#D0D5DD;align=center;verticalAlign=middle;shadow=0;" vertex="1" parent="1">
          <mxGeometry x="40" y="20" width="1500" height="60" as="geometry" />
        </mxCell>

        <!-- SECAO: FONTE PRIMARIA DE ENERGIA -->
        <mxCell id="group_battery" value="FONTE PRIMARIA DE ENERGIA (12V DC)" style="swimlane;whiteSpace=wrap;html=1;fillColor=#F9FAFB;strokeColor=#EAECF0;fontStyle=1;startSize=26;fontSize=12;fontColor=#1D2939;" vertex="1" parent="1">
          <mxGeometry x="40" y="100" width="290" height="400" as="geometry" />
        </mxCell>

        <mxCell id="bat01" value="&lt;b style=&quot;font-size:14px;&quot;&gt;BAT-01&lt;/b&gt;&lt;br&gt;MK ES17-12&lt;br&gt;Chumbo-Acido AGM&lt;br&gt;&lt;b&gt;12 V / 18 Ah&lt;/b&gt;&lt;br&gt;&lt;i style=&quot;font-size:11px;&quot;&gt;Terminais F3 - M5&lt;/i&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FEE4E2;strokeColor=#D92D20;strokeWidth=2;fontColor=#B42318;" vertex="1" parent="group_battery">
          <mxGeometry x="30" y="45" width="230" height="90" as="geometry" />
        </mxCell>

        <mxCell id="qg01" value="&lt;b style=&quot;font-size:14px;&quot;&gt;QG-01&lt;/b&gt;&lt;br&gt;Chave Geral DC&lt;br&gt;&lt;span style=&quot;font-size:11px; color:#B54708;&quot;&gt;Seccionamento Master&lt;br&gt;Corte Mecanico 100A+&lt;/span&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FEF0C7;strokeColor=#DC6803;strokeWidth=2;fontColor=#B54708;" vertex="1" parent="group_battery">
          <mxGeometry x="30" y="180" width="230" height="80" as="geometry" />
        </mxCell>

        <mxCell id="wire_bat_qg" value="BAT+ (4 AWG)" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#D92D20;strokeWidth=4;labelBackgroundColor=#FFFFFF;fontColor=#D92D20;fontStyle=1;exitX=0.5;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="group_battery" source="bat01" target="qg01">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <mxCell id="group_battery_notes" value="Condutores 4 AWG:&lt;br&gt;Risco minimo de queda de tensao sob corrente de pico dos motores CIM." style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=10;fontColor=#667085;" vertex="1" parent="group_battery">
          <mxGeometry x="20" y="280" width="250" height="50" as="geometry" />
        </mxCell>

        <!-- BARRAMENTOS PDB-01 (+12V e 0V) -->
        <mxCell id="pdb_bus_pos" value="&lt;b style=&quot;font-size:13px;&quot;&gt;PDB-01 : BARRAMENTO +12 V DC (DISTRIBUICAO PRINCIPAL)&lt;/b&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#D92D20;strokeColor=#B42318;fontColor=#FFFFFF;fontStyle=1;align=center;" vertex="1" parent="1">
          <mxGeometry x="360" y="100" width="1180" height="35" as="geometry" />
        </mxCell>

        <mxCell id="wire_qg_busp" value="4 AWG (+12V)" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#D92D20;strokeWidth=4;labelBackgroundColor=#FFFFFF;fontColor=#D92D20;fontStyle=1;exitX=1;exitY=0.5;entryX=0;entryY=0.5;" edge="1" parent="1" source="qg01" target="pdb_bus_pos">
          <mxGeometry relative="1" as="geometry">
            <Array as="points">
              <mxPoint x="320" y="320" />
              <mxPoint x="320" y="118" />
            </Array>
          </mxGeometry>
        </mxCell>

        <mxCell id="pdb_bus_neg" value="&lt;b style=&quot;font-size:13px;&quot;&gt;PDB-01 : BARRAMENTO 0 V / GND (RETORNO DE POTENCIA UNIFICADO)&lt;/b&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#1D2939;strokeColor=#101828;fontColor=#FFFFFF;fontStyle=1;align=center;" vertex="1" parent="1">
          <mxGeometry x="360" y="800" width="1180" height="35" as="geometry" />
        </mxCell>

        <mxCell id="wire_bat_busn" value="BAT- / 4 AWG (0V GND)" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#1D2939;strokeWidth=4;labelBackgroundColor=#FFFFFF;fontColor=#1D2939;fontStyle=1;exitX=0;exitY=0.5;entryX=0;entryY=0.5;" edge="1" parent="1" source="bat01" target="pdb_bus_neg">
          <mxGeometry relative="1" as="geometry">
            <Array as="points">
              <mxPoint x="20" y="190" />
              <mxPoint x="20" y="818" />
            </Array>
          </mxGeometry>
        </mxCell>

        <!-- SECAO: CIRCUITO DE SEGURANCA FISICA (E-STOP & INTERTRAVAMENTO) -->
        <mxCell id="group_safety" value="CIRCUITO DE SEGURANCA FISICA (E-STOP)" style="swimlane;whiteSpace=wrap;html=1;fillColor=#FFF6ED;strokeColor=#F95738;fontStyle=1;startSize=24;fontSize=11;fontColor=#7A271A;" vertex="1" parent="1">
          <mxGeometry x="40" y="520" width="290" height="315" as="geometry" />
        </mxCell>

        <mxCell id="emg01" value="&lt;b style=&quot;font-size:13px;&quot;&gt;EMG-01&lt;/b&gt;&lt;br&gt;Botao de Emergencia Cogumelo&lt;br&gt;&lt;b&gt;Contato Duplo NC (NF)&lt;/b&gt;&lt;br&gt;&lt;i style=&quot;font-size:10px; color:#B42318;&quot;&gt;Abertura Mecanica Forcada&lt;/i&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FEE4E2;strokeColor=#D92D20;fontColor=#B42318;strokeWidth=2;" vertex="1" parent="group_safety">
          <mxGeometry x="25" y="35" width="240" height="80" as="geometry" />
        </mxCell>

        <mxCell id="sr01" value="&lt;b style=&quot;font-size:13px;&quot;&gt;SR-01&lt;/b&gt;&lt;br&gt;Rele / Modulo de Seguranca&lt;br&gt;&lt;span style=&quot;font-size:11px; color:#475467;&quot;&gt;Intertravamento de Bobina K1&lt;br&gt;Monitoramento de Falhas&lt;/span&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FEF3F2;strokeColor=#F04438;fontColor=#912018;strokeWidth=2;" vertex="1" parent="group_safety">
          <mxGeometry x="25" y="150" width="240" height="75" as="geometry" />
        </mxCell>

        <mxCell id="wire_emg_sr" value="Canal NC" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#D92D20;strokeWidth=2;fontColor=#B42318;fontStyle=1;exitX=0.5;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="group_safety" source="emg01" target="sr01">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <mxCell id="safety_badge" value="CATEGORIA DE SEGURANCA NR-12&lt;br&gt;Corte de hardware redundante" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=10;fontColor=#B42318;fontStyle=1;" vertex="1" parent="group_safety">
          <mxGeometry x="20" y="240" width="250" height="40" as="geometry" />
        </mxCell>

        <!-- RAMAL 1: LOGICA, PROCESSAMENTO E SENSORES (5.1V) -->
        <mxCell id="group_logic" value="RAMAL 1: LOGICA / COMPUTAÇÃO / SENSORES" style="swimlane;whiteSpace=wrap;html=1;fillColor=#F0F9FF;strokeColor=#B9E6FE;fontStyle=1;startSize=26;fontSize=11;fontColor=#026AA2;" vertex="1" parent="1">
          <mxGeometry x="360" y="160" width="270" height="610" as="geometry" />
        </mxCell>

        <mxCell id="f01" value="&lt;b&gt;F01&lt;/b&gt;&lt;br&gt;Fusivel 5 A&lt;br&gt;&lt;i style=&quot;font-size:10px;&quot;&gt;Protecao Preliminar DC-01&lt;/i&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FEF0C7;strokeColor=#DC6803;fontColor=#B54708;strokeWidth=1.5;" vertex="1" parent="group_logic">
          <mxGeometry x="45" y="40" width="180" height="50" as="geometry" />
        </mxCell>

        <mxCell id="dc01" value="&lt;b style=&quot;font-size:13px;&quot;&gt;DC-01&lt;/b&gt;&lt;br&gt;Conversor Step-Down DC/DC&lt;br&gt;&lt;b&gt;Entrada: 12V | Saida: 5,1V / 5A&lt;/b&gt;&lt;br&gt;&lt;span style=&quot;font-size:10px; color:#026AA2;&quot;&gt;Isolado de transientes de motor&lt;/span&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E0F2FE;strokeColor=#0284C7;fontColor=#026AA2;strokeWidth=2;" vertex="1" parent="group_logic">
          <mxGeometry x="35" y="125" width="200" height="75" as="geometry" />
        </mxCell>

        <mxCell id="v5_bus" value="&lt;b&gt;BUS-5V&lt;/b&gt;&lt;br&gt;Barramento 5,1 V Lógica" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#0284C7;strokeColor=#0369A1;fontColor=#FFFFFF;fontStyle=1;align=center;" vertex="1" parent="group_logic">
          <mxGeometry x="25" y="235" width="220" height="35" as="geometry" />
        </mxCell>

        <mxCell id="pi01" value="&lt;b style=&quot;font-size:13px;&quot;&gt;RPI-01&lt;/b&gt;&lt;br&gt;Raspberry Pi 3B (ROS 2 Humble)&lt;br&gt;&lt;span style=&quot;font-size:10px; color:#475467;&quot;&gt;Consumo ~2.5A máx (Câmera + HAL)&lt;/span&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F8F9FA;strokeColor=#667085;fontColor=#1D2939;strokeWidth=1.5;" vertex="1" parent="group_logic">
          <mxGeometry x="35" y="300" width="200" height="60" as="geometry" />
        </mxCell>

        <mxCell id="esp01" value="&lt;b style=&quot;font-size:13px;&quot;&gt;ESP-01&lt;/b&gt;&lt;br&gt;ESP32 DevKit v1&lt;br&gt;&lt;span style=&quot;font-size:10px; color:#475467;&quot;&gt;Firmware PID / Encoders / Watchdog&lt;/span&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F8F9FA;strokeColor=#667085;fontColor=#1D2939;strokeWidth=1.5;" vertex="1" parent="group_logic">
          <mxGeometry x="35" y="390" width="200" height="60" as="geometry" />
        </mxCell>

        <mxCell id="sensores" value="&lt;b style=&quot;font-size:13px;&quot;&gt;SEN (Sensores 5V)&lt;/b&gt;&lt;br&gt;HC-SR04, LiDAR A1, Encoders&lt;br&gt;&lt;span style=&quot;font-size:10px; color:#475467;&quot;&gt;Alimentação Lógica Protegida&lt;/span&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F8F9FA;strokeColor=#667085;fontColor=#1D2939;strokeWidth=1.5;" vertex="1" parent="group_logic">
          <mxGeometry x="35" y="480" width="200" height="60" as="geometry" />
        </mxCell>

        <!-- Conexoes Internas Ramo 1 -->
        <mxCell id="wire_busp_f01" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#D92D20;strokeWidth=3;exitX=0.15;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="1" source="pdb_bus_pos" target="f01">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <mxCell id="wire_f01_dc01" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#D92D20;strokeWidth=3;exitX=0.5;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="group_logic" source="f01" target="dc01">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <mxCell id="wire_dc01_v5" value="+5,1 V" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#0284C7;strokeWidth=3;fontColor=#0284C7;fontStyle=1;exitX=0.5;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="group_logic" source="dc01" target="v5_bus">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <mxCell id="wire_v5_pi" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#0284C7;strokeWidth=2;exitX=0.5;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="group_logic" source="v5_bus" target="pi01">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <mxCell id="wire_v5_esp" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#0284C7;strokeWidth=2;exitX=0.5;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="group_logic" source="pi01" target="esp01">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <mxCell id="wire_v5_sen" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#0284C7;strokeWidth=2;exitX=0.5;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="group_logic" source="esp01" target="sensores">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <!-- Retorno 0V DC-01 para BUSN -->
        <mxCell id="wire_dc01_busn" value="Retorno 0V GND" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#1D2939;strokeWidth=2;fontColor=#1D2939;exitX=0.85;exitY=1;entryX=0.15;entryY=0;" edge="1" parent="1" source="dc01" target="pdb_bus_neg">
          <mxGeometry relative="1" as="geometry">
            <Array as="points">
              <mxPoint x="580" y="380" />
              <mxPoint x="580" y="770" />
              <mxPoint x="537" y="770" />
            </Array>
          </mxGeometry>
        </mxCell>

        <!-- RAMAL 2: SINALIZACAO VISUAL LED RGB -->
        <mxCell id="group_rgb" value="RAMAL 2: SINALIZACAO LED RGB" style="swimlane;whiteSpace=wrap;html=1;fillColor=#FDF2FA;strokeColor=#FCCEEE;fontStyle=1;startSize=26;fontSize=11;fontColor=#C11574;" vertex="1" parent="1">
          <mxGeometry x="655" y="160" width="230" height="610" as="geometry" />
        </mxCell>

        <mxCell id="f04" value="&lt;b&gt;F04&lt;/b&gt;&lt;br&gt;Fusivel 1 A&lt;br&gt;&lt;i style=&quot;font-size:10px;&quot;&gt;Proteção LEDs 12V&lt;/i&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FEF0C7;strokeColor=#DC6803;fontColor=#B54708;strokeWidth=1.5;" vertex="1" parent="group_rgb">
          <mxGeometry x="35" y="40" width="160" height="50" as="geometry" />
        </mxCell>

        <mxCell id="rgb_drv" value="&lt;b style=&quot;font-size:13px;&quot;&gt;LED-DRV&lt;/b&gt;&lt;br&gt;Driver 3 Canais MOSFET&lt;br&gt;&lt;span style=&quot;font-size:10px; color:#C11574;&quot;&gt;Comutação R, G, B via PWM ESP32&lt;/span&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FCE7F6;strokeColor=#EE46BC;fontColor=#9E165F;strokeWidth=2;" vertex="1" parent="group_rgb">
          <mxGeometry x="25" y="140" width="180" height="70" as="geometry" />
        </mxCell>

        <mxCell id="led01" value="&lt;b style=&quot;font-size:13px;&quot;&gt;LED-01&lt;/b&gt;&lt;br&gt;Fita / Barra RGB 5050&lt;br&gt;&lt;b&gt;12 V DC Anodo Comum&lt;/b&gt;&lt;br&gt;&lt;span style=&quot;font-size:10px; color:#475467;&quot;&gt;Sinalização de Estados do Robô&lt;/span&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F8F9FA;strokeColor=#C11574;fontColor=#1D2939;strokeWidth=1.5;" vertex="1" parent="group_rgb">
          <mxGeometry x="25" y="270" width="180" height="80" as="geometry" />
        </mxCell>

        <mxCell id="rgb_states_box" value="3 ESTADOS VISUAIS:&lt;br&gt;&lt;b style=&quot;color:#027A48;&quot;&gt;VERDE:&lt;/b&gt; Autonomia / Movimento&lt;br&gt;&lt;b style=&quot;color:#B54708;&quot;&gt;AMARELO:&lt;/b&gt; Standby / Manual&lt;br&gt;&lt;b style=&quot;color:#B42318;&quot;&gt;VERMELHO:&lt;/b&gt; E-Stop / Falha" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#EAECF0;align=left;fontSize=10;fontColor=#344054;" vertex="1" parent="group_rgb">
          <mxGeometry x="15" y="380" width="200" height="90" as="geometry" />
        </mxCell>

        <mxCell id="wire_busp_f04" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#D92D20;strokeWidth=3;exitX=0.32;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="1" source="pdb_bus_pos" target="f04">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <mxCell id="wire_f04_rgb" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#D92D20;strokeWidth=3;exitX=0.5;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="group_rgb" source="f04" target="rgb_drv">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <mxCell id="wire_rgb_led" value="R, G, B Chaveados" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#EE46BC;strokeWidth=2;fontColor=#9E165F;fontStyle=1;exitX=0.5;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="group_rgb" source="rgb_drv" target="led01">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <mxCell id="wire_rgb_busn" value="Retorno 0V" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#1D2939;strokeWidth=2;fontColor=#1D2939;exitX=0.8;exitY=1;entryX=0.35;entryY=0;" edge="1" parent="1" source="rgb_drv" target="pdb_bus_neg">
          <mxGeometry relative="1" as="geometry">
            <Array as="points">
              <mxPoint x="824" y="420" />
              <mxPoint x="824" y="770" />
              <mxPoint x="773" y="770" />
            </Array>
          </mxGeometry>
        </mxCell>

        <!-- RAMAL 3: TRACAO & POTENCIA DOS MOTORES CIM + SPARK MAX -->
        <mxCell id="group_motors" value="RAMAL 3: CIRCUITO DE TRACAO / MOTORES CIM (CORTE VMOT VIA K1)" style="swimlane;whiteSpace=wrap;html=1;fillColor=#ECFDF3;strokeColor=#A6F4C5;fontStyle=1;startSize=26;fontSize=11;fontColor=#027A48;" vertex="1" parent="1">
          <mxGeometry x="910" y="160" width="630" height="610" as="geometry" />
        </mxCell>

        <!-- Canal Esquerdo -->
        <mxCell id="f02" value="&lt;b&gt;F02&lt;/b&gt;&lt;br&gt;Fusível Motor Esquerdo&lt;br&gt;&lt;b style=&quot;color:#B42318;&quot;&gt;30 A a 40 A (A dimensionar)&lt;/b&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FEF0C7;strokeColor=#DC6803;fontColor=#B54708;strokeWidth=2;" vertex="1" parent="group_motors">
          <mxGeometry x="40" y="40" width="220" height="55" as="geometry" />
        </mxCell>

        <mxCell id="k1a" value="&lt;b style=&quot;font-size:13px;&quot;&gt;K1 (Contato K1A)&lt;/b&gt;&lt;br&gt;Contato de Potência Motor Esq.&lt;br&gt;&lt;span style=&quot;font-size:10px; color:#B42318;&quot;&gt;Corte Galvanico Imediato por SR-01&lt;/span&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FEE4E2;strokeColor=#D92D20;fontColor=#B42318;strokeWidth=2;" vertex="1" parent="group_motors">
          <mxGeometry x="40" y="130" width="220" height="65" as="geometry" />
        </mxCell>

        <mxCell id="mc01" value="&lt;b style=&quot;font-size:14px;&quot;&gt;MC-01&lt;/b&gt;&lt;br&gt;REV Spark MAX (Esquerdo)&lt;br&gt;Driver DC / PWM / CAN&lt;br&gt;&lt;span style=&quot;font-size:10px; color:#344054;&quot;&gt;Alimentação: 12V VMOT / 0V&lt;/span&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#D1FADF;strokeColor=#12B76A;fontColor=#027A48;strokeWidth=2;" vertex="1" parent="group_motors">
          <mxGeometry x="40" y="240" width="220" height="80" as="geometry" />
        </mxCell>

        <mxCell id="m01" value="&lt;b style=&quot;font-size:14px;&quot;&gt;MOT-01&lt;/b&gt;&lt;br&gt;Motor DC AndyMark CIM Esquerdo&lt;br&gt;12 V DC • 5310 RPM • 133A Stall&lt;br&gt;&lt;b style=&quot;color:#1D2939;&quot;&gt;Tração Roda Esquerda&lt;/b&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F2F4F7;strokeColor=#475467;fontColor=#1D2939;strokeWidth=2;" vertex="1" parent="group_motors">
          <mxGeometry x="40" y="380" width="220" height="85" as="geometry" />
        </mxCell>

        <!-- Canal Direito -->
        <mxCell id="f03" value="&lt;b&gt;F03&lt;/b&gt;&lt;br&gt;Fusível Motor Direito&lt;br&gt;&lt;b style=&quot;color:#B42318;&quot;&gt;30 A a 40 A (A dimensionar)&lt;/b&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FEF0C7;strokeColor=#DC6803;fontColor=#B54708;strokeWidth=2;" vertex="1" parent="group_motors">
          <mxGeometry x="370" y="40" width="220" height="55" as="geometry" />
        </mxCell>

        <mxCell id="k1b" value="&lt;b style=&quot;font-size:13px;&quot;&gt;K1 (Contato K1B)&lt;/b&gt;&lt;br&gt;Contato de Potência Motor Dir.&lt;br&gt;&lt;span style=&quot;font-size:10px; color:#B42318;&quot;&gt;Corte Galvanico Imediato por SR-01&lt;/span&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FEE4E2;strokeColor=#D92D20;fontColor=#B42318;strokeWidth=2;" vertex="1" parent="group_motors">
          <mxGeometry x="370" y="130" width="220" height="65" as="geometry" />
        </mxCell>

        <mxCell id="mc02" value="&lt;b style=&quot;font-size:14px;&quot;&gt;MC-02&lt;/b&gt;&lt;br&gt;REV Spark MAX (Direito)&lt;br&gt;Driver DC / PWM / CAN&lt;br&gt;&lt;span style=&quot;font-size:10px; color:#344054;&quot;&gt;Alimentação: 12V VMOT / 0V&lt;/span&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#D1FADF;strokeColor=#12B76A;fontColor=#027A48;strokeWidth=2;" vertex="1" parent="group_motors">
          <mxGeometry x="370" y="240" width="220" height="80" as="geometry" />
        </mxCell>

        <mxCell id="m02" value="&lt;b style=&quot;font-size:14px;&quot;&gt;MOT-02&lt;/b&gt;&lt;br&gt;Motor DC AndyMark CIM Direito&lt;br&gt;12 V DC • 5310 RPM • 133A Stall&lt;br&gt;&lt;b style=&quot;color:#1D2939;&quot;&gt;Tração Roda Direita&lt;/b&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F2F4F7;strokeColor=#475467;fontColor=#1D2939;strokeWidth=2;" vertex="1" parent="group_motors">
          <mxGeometry x="370" y="380" width="220" height="85" as="geometry" />
        </mxCell>

        <!-- Conexoes Motor Esquerdo -->
        <mxCell id="wire_busp_f02" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#D92D20;strokeWidth=4;exitX=0.55;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="1" source="pdb_bus_pos" target="f02">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <mxCell id="wire_f02_k1a" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#D92D20;strokeWidth=4;exitX=0.5;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="group_motors" source="f02" target="k1a">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <mxCell id="wire_k1a_mc01" value="+12V VMOT (10-12 AWG)" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#D92D20;strokeWidth=4;fontColor=#B42318;fontStyle=1;exitX=0.5;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="group_motors" source="k1a" target="mc01">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <mxCell id="wire_mc01_m01" value="Saída Motor CIM M+ / M-" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#12B76A;strokeWidth=3;fontColor=#027A48;fontStyle=1;exitX=0.5;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="group_motors" source="mc01" target="m01">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <!-- Conexoes Motor Direito -->
        <mxCell id="wire_busp_f03" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#D92D20;strokeWidth=4;exitX=0.85;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="1" source="pdb_bus_pos" target="f03">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <mxCell id="wire_f03_k1b" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#D92D20;strokeWidth=4;exitX=0.5;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="group_motors" source="f03" target="k1b">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <mxCell id="wire_k1b_mc02" value="+12V VMOT (10-12 AWG)" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#D92D20;strokeWidth=4;fontColor=#B42318;fontStyle=1;exitX=0.5;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="group_motors" source="k1b" target="mc02">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <mxCell id="wire_mc02_m02" value="Saída Motor CIM M+ / M-" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#12B76A;strokeWidth=3;fontColor=#027A48;fontStyle=1;exitX=0.5;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="group_motors" source="mc02" target="m02">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <!-- Retorno 0V GND dos Spark MAX -->
        <mxCell id="wire_mc01_busn" value="0V GND (10-12 AWG)" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#1D2939;strokeWidth=4;fontColor=#1D2939;exitX=0.2;exitY=1;entryX=0.65;entryY=0;" edge="1" parent="1" source="mc01" target="pdb_bus_neg">
          <mxGeometry relative="1" as="geometry">
            <Array as="points">
              <mxPoint x="994" y="770" />
              <mxPoint x="1127" y="770" />
            </Array>
          </mxGeometry>
        </mxCell>

        <mxCell id="wire_mc02_busn" value="0V GND (10-12 AWG)" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#1D2939;strokeWidth=4;fontColor=#1D2939;exitX=0.8;exitY=1;entryX=0.88;entryY=0;" edge="1" parent="1" source="mc02" target="pdb_bus_neg">
          <mxGeometry relative="1" as="geometry">
            <Array as="points">
              <mxPoint x="1456" y="770" />
              <mxPoint x="1398" y="770" />
            </Array>
          </mxGeometry>
        </mxCell>

        <!-- SINAIS DE CONTROLE E INTERTRAVAMENTO (TRACEJADOS) -->
        <mxCell id="wire_sr_k1a" value="Comanda abertura K1A" style="edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#D92D20;strokeWidth=2;dashed=1;fontColor=#D92D20;fontStyle=1;exitX=1;exitY=0.3;entryX=0;entryY=0.5;" edge="1" parent="1" source="sr01" target="k1a">
          <mxGeometry relative="1" as="geometry">
            <Array as="points">
              <mxPoint x="340" y="690" />
              <mxPoint x="340" y="322" />
            </Array>
          </mxGeometry>
        </mxCell>

        <mxCell id="wire_sr_k1b" value="Comanda abertura K1B" style="edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#D92D20;strokeWidth=2;dashed=1;fontColor=#D92D20;fontStyle=1;exitX=1;exitY=0.7;entryX=0;entryY=0.5;" edge="1" parent="1" source="sr01" target="k1b">
          <mxGeometry relative="1" as="geometry">
            <Array as="points">
              <mxPoint x="350" y="720" />
              <mxPoint x="350" y="340" />
              <mxPoint x="1270" y="340" />
              <mxPoint x="1270" y="322" />
            </Array>
          </mxGeometry>
        </mxCell>

        <mxCell id="wire_emg_esp" value="Contato Auxiliar E-Stop -&gt; ESP32 (GPIO 34)" style="edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#444CE7;strokeWidth=2;dashed=1;fontColor=#3538CD;fontStyle=1;exitX=1;exitY=0.5;entryX=0;entryY=0.5;" edge="1" parent="1" source="emg01" target="esp01">
          <mxGeometry relative="1" as="geometry">
            <Array as="points">
              <mxPoint x="345" y="595" />
              <mxPoint x="345" y="580" />
            </Array>
          </mxGeometry>
        </mxCell>

        <!-- NOTAS DE ENGENHARIA NO RODAPE -->
        <mxCell id="footer_notes" value="&lt;b style=&quot;font-size:12px; color:#1D2939;&quot;&gt;NOTAS DE DIMENSIONAMENTO E ENGENHARIA ELETRICA (NORMA NR-12 / IEC 60204-1):&lt;/b&gt;&lt;br&gt;&lt;b style=&quot;color:#B42318;&quot;&gt;1. Cabos de Força (4 AWG):&lt;/b&gt; Interligação BAT-01 -&gt; QG-01 -&gt; Barramentos PDB-01 (+12V e 0V) suportam picos transitórios de até 130A dos motores CIM em rampa de aceleração.&lt;br&gt;&lt;b style=&quot;color:#B54708;&quot;&gt;2. Proteção Motores F02 / F03:&lt;/b&gt; Dimensionar entre 30A e 40A por motor (fusíveis tipo MAXI ou disjuntores automotivos térmicos Snap Action para proteção contra travamento).&lt;br&gt;&lt;b style=&quot;color:#027A48;&quot;&gt;3. Desconexão Segura Fail-Safe:&lt;/b&gt; Abertura do botão EMG-01 desenergiza a bobina do contator K1, abrindo K1A e K1B e eliminando a energia mecânica dos motores.&lt;br&gt;&lt;b style=&quot;color:#026AA2;&quot;&gt;4. Estabilidade Lógica:&lt;/b&gt; Conversor DC-01 dedicado de 5,1V / 5A mantém alimentação estável da Raspberry Pi 3B e ESP32 imune a quedas de tensão na bateria." style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F8F9FA;strokeColor=#D0D5DD;align=left;verticalAlign=middle;fontSize=10;fontColor=#344054;spacingLeft=15;" vertex="1" parent="1">
          <mxGeometry x="40" y="855" width="1500" height="95" as="geometry" />
        </mxCell>

      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''
    return xml

def get_svg():
    svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1020" width="100%" height="100%" style="background-color: #FFFFFF; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <defs>
    <filter id="boxShadow" x="-5%" y="-5%" width="110%" height="115%" filterUnits="userSpaceOnUse">
      <feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#000000" flood-opacity="0.08" />
    </filter>
    
    <marker id="arrowRed" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#D92D20" />
    </marker>
    <marker id="arrowDark" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#1D2939" />
    </marker>
    <marker id="arrowBlue" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#0284C7" />
    </marker>
    <marker id="arrowGreen" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#12B76A" />
    </marker>
    <marker id="arrowPink" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#EE46BC" />
    </marker>
  </defs>

  <!-- CABECALHO / TITULO -->
  <rect x="40" y="20" width="1520" height="65" rx="8" fill="#F8F9FA" stroke="#D0D5DD" stroke-width="1.5" />
  <text x="800" y="47" text-anchor="middle" font-size="20" font-weight="700" fill="#1D2939">DIAGRAMA ELETRICO UNIFILAR / MULTIFILAR - CIRCUITO DE POTENCIA AGV</text>
  <text x="800" y="69" text-anchor="middle" font-size="13" font-weight="500" fill="#475467">Projeto AGV / AMR Autonomo • Tensao Nominal: 12V DC • Bateria MK ES17-12 (18 Ah) • Arquitetura Fail-Safe ISO 13849 / NR-12</text>

  <!-- SECAO 1: BATERIA E FONTE PRIMARIA -->
  <g id="secao_bateria">
    <rect x="40" y="105" width="290" height="395" rx="8" fill="#F9FAFB" stroke="#EAECF0" stroke-width="2" />
    <rect x="40" y="105" width="290" height="30" rx="8" fill="#EAECF0" />
    <text x="185" y="125" text-anchor="middle" font-size="12" font-weight="700" fill="#344054">FONTE PRIMARIA DE ENERGIA (12V DC)</text>

    <!-- BAT-01 -->
    <rect x="65" y="150" width="240" height="90" rx="8" fill="#FEE4E2" stroke="#D92D20" stroke-width="2" filter="url(#boxShadow)" />
    <text x="185" y="177" text-anchor="middle" font-size="15" font-weight="700" fill="#B42318">BAT-01</text>
    <text x="185" y="197" text-anchor="middle" font-size="13" font-weight="600" fill="#344054">MK ES17-12 (AGM)</text>
    <text x="185" y="215" text-anchor="middle" font-size="14" font-weight="700" fill="#D92D20">12 V / 18 Ah</text>
    <text x="185" y="230" text-anchor="middle" font-size="11" font-weight="500" fill="#475467">Terminais F3 - M5</text>

    <!-- Linha BAT+ -> QG-01 (4 AWG) -->
    <line x1="185" y1="240" x2="185" y2="285" stroke="#D92D20" stroke-width="5" marker-end="url(#arrowRed)" />
    <rect x="135" y="252" width="100" height="20" rx="4" fill="#FFFFFF" stroke="#D92D20" stroke-width="1" />
    <text x="185" y="266" text-anchor="middle" font-size="10" font-weight="700" fill="#D92D20">BAT+ (4 AWG)</text>

    <!-- QG-01 -->
    <rect x="65" y="285" width="240" height="80" rx="8" fill="#FEF0C7" stroke="#DC6803" stroke-width="2" filter="url(#boxShadow)" />
    <text x="185" y="312" text-anchor="middle" font-size="15" font-weight="700" fill="#B54708">QG-01</text>
    <text x="185" y="332" text-anchor="middle" font-size="13" font-weight="600" fill="#344054">Chave Geral DC</text>
    <text x="185" y="348" text-anchor="middle" font-size="11" font-weight="500" fill="#475467">Corte Mecanico Master (100A+)</text>

    <!-- Nota Informativa -->
    <text x="185" y="405" text-anchor="middle" font-size="10" font-weight="600" fill="#475467">Cabos Principais em Cobre 4 AWG</text>
    <text x="185" y="420" text-anchor="middle" font-size="9" font-weight="400" fill="#667085">Queda de tensao desprezivel sob picos de 130A</text>
  </g>

  <!-- BARRAMENTOS PDB-01 (+12V e 0V) -->
  <!-- Barramento Positivo +12V -->
  <rect x="360" y="105" width="1200" height="35" rx="6" fill="#D92D20" stroke="#B42318" stroke-width="2" filter="url(#boxShadow)" />
  <text x="960" y="128" text-anchor="middle" font-size="13" font-weight="700" fill="#FFFFFF">PDB-01 : BARRAMENTO +12 V DC (DISTRIBUICAO PRINCIPAL DE POTENCIA)</text>

  <!-- Alimentacao do Barramento Positivo vinda da QG-01 -->
  <path d="M 305 325 L 340 325 L 340 122 L 360 122" fill="none" stroke="#D92D20" stroke-width="5" marker-end="url(#arrowRed)" />
  <text x="345" y="225" font-size="10" font-weight="700" fill="#D92D20" transform="rotate(-90 345,225)">4 AWG (+12V)</text>

  <!-- Barramento Negativo 0V (GND) -->
  <rect x="360" y="795" width="1200" height="35" rx="6" fill="#1D2939" stroke="#101828" stroke-width="2" filter="url(#boxShadow)" />
  <text x="960" y="818" text-anchor="middle" font-size="13" font-weight="700" fill="#FFFFFF">PDB-01 : BARRAMENTO 0 V / GND (RETORNO DE POTENCIA UNIFICADO)</text>

  <!-- Retorno BAT- para BUSN (4 AWG) -->
  <path d="M 65 195 L 25 195 L 25 812 L 360 812" fill="none" stroke="#1D2939" stroke-width="5" marker-end="url(#arrowDark)" />
  <rect x="10" y="470" width="30" height="110" rx="4" fill="#FFFFFF" stroke="#1D2939" stroke-width="1" />
  <text x="25" y="525" text-anchor="middle" font-size="10" font-weight="700" fill="#1D2939" transform="rotate(-90 25,525)">BAT- (4 AWG GND)</text>

  <!-- SECAO 2: CIRCUITO DE SEGURANCA FISICA (E-STOP & INTERTRAVAMENTO) -->
  <g id="secao_seguranca">
    <rect x="40" y="520" width="290" height="310" rx="8" fill="#FFF6ED" stroke="#F95738" stroke-width="2" />
    <rect x="40" y="520" width="290" height="30" rx="8" fill="#FEE4E2" />
    <text x="185" y="540" text-anchor="middle" font-size="12" font-weight="700" fill="#B42318">CIRCUITO DE SEGURANCA FISICA (E-STOP)</text>

    <!-- EMG-01 -->
    <rect x="65" y="565" width="240" height="75" rx="8" fill="#FEE4E2" stroke="#D92D20" stroke-width="2" filter="url(#boxShadow)" />
    <text x="185" y="590" text-anchor="middle" font-size="14" font-weight="700" fill="#B42318">EMG-01</text>
    <text x="185" y="608" text-anchor="middle" font-size="12" font-weight="600" fill="#344054">Botao Cogumelo NC</text>
    <text x="185" y="624" text-anchor="middle" font-size="10" font-weight="500" fill="#B42318">Canal Duplo de Abertura Mecanica</text>

    <!-- Linha EMG-01 -> SR-01 -->
    <line x1="185" y1="640" x2="185" y2="675" stroke="#D92D20" stroke-width="3" marker-end="url(#arrowRed)" />

    <!-- SR-01 -->
    <rect x="65" y="675" width="240" height="75" rx="8" fill="#FEF3F2" stroke="#F04438" stroke-width="2" filter="url(#boxShadow)" />
    <text x="185" y="700" text-anchor="middle" font-size="14" font-weight="700" fill="#912018">SR-01</text>
    <text x="185" y="718" text-anchor="middle" font-size="12" font-weight="600" fill="#344054">Rele / Modulo de Seguranca</text>
    <text x="185" y="734" text-anchor="middle" font-size="10" font-weight="500" fill="#475467">Intertravamento Hardware da Bobina K1</text>

    <text x="185" y="785" text-anchor="middle" font-size="10" font-weight="700" fill="#B42318">NORMA NR-12 / ISO 13849-1</text>
    <text x="185" y="800" text-anchor="middle" font-size="9" font-weight="400" fill="#667085">Corte de potencia por desenergizacao ativa</text>
  </g>

  <!-- RAMAL 1: LOGICA, PROCESSAMENTO E SENSORES -->
  <g id="ramal_logica">
    <rect x="360" y="160" width="270" height="615" rx="8" fill="#F0F9FF" stroke="#B9E6FE" stroke-width="2" />
    <rect x="360" y="160" width="270" height="30" rx="8" fill="#E0F2FE" />
    <text x="495" y="180" text-anchor="middle" font-size="12" font-weight="700" fill="#026AA2">RAMAL 1: LOGICA / COMPUTAÇÃO</text>

    <!-- F01 -->
    <line x1="495" y1="140" x2="495" y2="205" stroke="#D92D20" stroke-width="3" marker-end="url(#arrowRed)" />
    <rect x="400" y="205" width="190" height="45" rx="6" fill="#FEF0C7" stroke="#DC6803" stroke-width="1.5" filter="url(#boxShadow)" />
    <text x="495" y="225" text-anchor="middle" font-size="13" font-weight="700" fill="#B54708">F01 (Fusivel 5 A)</text>
    <text x="495" y="240" text-anchor="middle" font-size="10" font-weight="500" fill="#475467">Protecao Linha Step-Down</text>

    <!-- DC-01 -->
    <line x1="495" y1="250" x2="495" y2="280" stroke="#D92D20" stroke-width="3" marker-end="url(#arrowRed)" />
    <rect x="385" y="280" width="220" height="70" rx="8" fill="#E0F2FE" stroke="#0284C7" stroke-width="2" filter="url(#boxShadow)" />
    <text x="495" y="303" text-anchor="middle" font-size="14" font-weight="700" fill="#026AA2">DC-01 (Step-Down DC/DC)</text>
    <text x="495" y="322" text-anchor="middle" font-size="12" font-weight="600" fill="#1D2939">Entrada: 12V • Saida: 5,1V / 5A</text>
    <text x="495" y="338" text-anchor="middle" font-size="10" font-weight="500" fill="#475467">Isolado contra brownout de motor</text>

    <!-- V5 BUS -->
    <line x1="495" y1="350" x2="495" y2="385" stroke="#0284C7" stroke-width="3" marker-end="url(#arrowBlue)" />
    <rect x="380" y="385" width="230" height="32" rx="6" fill="#0284C7" stroke="#0369A1" stroke-width="1.5" filter="url(#boxShadow)" />
    <text x="495" y="406" text-anchor="middle" font-size="12" font-weight="700" fill="#FFFFFF">BUS-5V (Barramento 5,1V Lógica)</text>

    <!-- RPI-01 -->
    <line x1="495" y1="417" x2="495" y2="445" stroke="#0284C7" stroke-width="2" marker-end="url(#arrowBlue)" />
    <rect x="390" y="445" width="210" height="55" rx="6" fill="#FFFFFF" stroke="#667085" stroke-width="1.5" filter="url(#boxShadow)" />
    <text x="495" y="468" text-anchor="middle" font-size="13" font-weight="700" fill="#1D2939">RPI-01 (Raspberry Pi 3B)</text>
    <text x="495" y="487" text-anchor="middle" font-size="10" font-weight="500" fill="#475467">ROS 2 Humble • Hal • Câmera USB</text>

    <!-- ESP-01 -->
    <line x1="495" y1="500" x2="495" y2="525" stroke="#0284C7" stroke-width="2" marker-end="url(#arrowBlue)" />
    <rect x="390" y="525" width="210" height="55" rx="6" fill="#FFFFFF" stroke="#667085" stroke-width="1.5" filter="url(#boxShadow)" />
    <text x="495" y="548" text-anchor="middle" font-size="13" font-weight="700" fill="#1D2939">ESP-01 (ESP32 DevKit)</text>
    <text x="495" y="567" text-anchor="middle" font-size="10" font-weight="500" fill="#475467">PID Motores • Encoders PCNT • Watchdog</text>

    <!-- SENSORES -->
    <line x1="495" y1="580" x2="495" y2="605" stroke="#0284C7" stroke-width="2" marker-end="url(#arrowBlue)" />
    <rect x="390" y="605" width="210" height="55" rx="6" fill="#FFFFFF" stroke="#667085" stroke-width="1.5" filter="url(#boxShadow)" />
    <text x="495" y="628" text-anchor="middle" font-size="13" font-weight="700" fill="#1D2939">SEN (Sensores do AGV)</text>
    <text x="495" y="647" text-anchor="middle" font-size="10" font-weight="500" fill="#475467">LiDAR RPLIDAR A1 • Ultrassom • Encoders</text>

    <!-- Retorno 0V DC-01 para BUSN -->
    <path d="M 590 350 L 610 350 L 610 750 L 495 750 L 495 795" fill="none" stroke="#1D2939" stroke-width="3" marker-end="url(#arrowDark)" />
    <text x="615" y="550" font-size="10" font-weight="700" fill="#1D2939" transform="rotate(-90 615,550)">Retorno 0V DC-01</text>
  </g>

  <!-- RAMAL 2: SINALIZACAO VISUAL LED RGB -->
  <g id="ramal_rgb">
    <rect x="655" y="160" width="230" height="615" rx="8" fill="#FDF2FA" stroke="#FCCEEE" stroke-width="2" />
    <rect x="655" y="160" width="230" height="30" rx="8" fill="#FCE7F6" />
    <text x="770" y="180" text-anchor="middle" font-size="12" font-weight="700" fill="#C11574">RAMAL 2: SINALIZACAO RGB</text>

    <!-- F04 -->
    <line x1="770" y1="140" x2="770" y2="210" stroke="#D92D20" stroke-width="3" marker-end="url(#arrowRed)" />
    <rect x="690" y="210" width="160" height="45" rx="6" fill="#FEF0C7" stroke="#DC6803" stroke-width="1.5" filter="url(#boxShadow)" />
    <text x="770" y="230" text-anchor="middle" font-size="13" font-weight="700" fill="#B54708">F04 (Fusivel 1 A)</text>
    <text x="770" y="245" text-anchor="middle" font-size="10" font-weight="500" fill="#475467">Protecao Linha LEDs</text>

    <!-- LED-DRV -->
    <line x1="770" y1="255" x2="770" y2="290" stroke="#D92D20" stroke-width="3" marker-end="url(#arrowRed)" />
    <rect x="675" y="290" width="190" height="65" rx="8" fill="#FCE7F6" stroke="#EE46BC" stroke-width="2" filter="url(#boxShadow)" />
    <text x="770" y="315" text-anchor="middle" font-size="14" font-weight="700" fill="#9E165F">LED-DRV</text>
    <text x="770" y="333" text-anchor="middle" font-size="11" font-weight="600" fill="#344054">3 Canais MOSFET (12V)</text>
    <text x="770" y="347" text-anchor="middle" font-size="9" font-weight="500" fill="#475467">Controle PWM vindo do ESP32</text>

    <!-- LED-01 -->
    <line x1="770" y1="355" x2="770" y2="395" stroke="#EE46BC" stroke-width="2.5" marker-end="url(#arrowPink)" />
    <rect x="675" y="395" width="190" height="65" rx="8" fill="#FFFFFF" stroke="#C11574" stroke-width="1.5" filter="url(#boxShadow)" />
    <text x="770" y="420" text-anchor="middle" font-size="14" font-weight="700" fill="#1D2939">LED-01</text>
    <text x="770" y="438" text-anchor="middle" font-size="11" font-weight="600" fill="#344054">Fita RGB 5050 (12V)</text>
    <text x="770" y="452" text-anchor="middle" font-size="9" font-weight="500" fill="#475467">Anodo Comum no +12V</text>

    <!-- Estados Visuais -->
    <rect x="670" y="490" width="200" height="110" rx="6" fill="#FFFFFF" stroke="#EAECF0" />
    <text x="770" y="512" text-anchor="middle" font-size="11" font-weight="700" fill="#1D2939">ESTADOS VISUAIS HMI:</text>
    <circle cx="690" cy="535" r="6" fill="#12B76A" />
    <text x="705" y="539" font-size="10" font-weight="600" fill="#027A48">VERDE: Autonomia / Operação</text>
    <circle cx="690" cy="560" r="6" fill="#F79009" />
    <text x="705" y="564" font-size="10" font-weight="600" fill="#B54708">AMARELO: Standby / Manual</text>
    <circle cx="690" cy="585" r="6" fill="#F04438" />
    <text x="705" y="589" font-size="10" font-weight="600" fill="#B42318">VERMELHO: E-Stop / Falha</text>

    <!-- Retorno 0V LED-DRV para BUSN -->
    <path d="M 850 355 L 870 355 L 870 750 L 770 750 L 770 795" fill="none" stroke="#1D2939" stroke-width="3" marker-end="url(#arrowDark)" />
    <text x="875" y="550" font-size="10" font-weight="700" fill="#1D2939" transform="rotate(-90 875,550)">Retorno 0V LED-DRV</text>
  </g>

  <!-- RAMAL 3: TRACAO & POTENCIA DOS MOTORES CIM + SPARK MAX -->
  <g id="ramal_motores">
    <rect x="910" y="160" width="650" height="615" rx="8" fill="#ECFDF3" stroke="#A6F4C5" stroke-width="2" />
    <rect x="910" y="160" width="650" height="30" rx="8" fill="#D1FADF" />
    <text x="1235" y="180" text-anchor="middle" font-size="12" font-weight="700" fill="#027A48">RAMAL 3: CIRCUITO DE TRACAO / MOTORES CIM (CORTE VMOT VIA CONTATOR K1)</text>

    <!-- CANAL MOTOR ESQUERDO -->
    <!-- F02 -->
    <line x1="1040" y1="140" x2="1040" y2="210" stroke="#D92D20" stroke-width="4" marker-end="url(#arrowRed)" />
    <rect x="940" y="210" width="200" height="50" rx="6" fill="#FEF0C7" stroke="#DC6803" stroke-width="2" filter="url(#boxShadow)" />
    <text x="1040" y="230" text-anchor="middle" font-size="13" font-weight="700" fill="#B54708">F02 (Motor Esquerdo)</text>
    <text x="1040" y="247" text-anchor="middle" font-size="11" font-weight="700" fill="#B42318">30 A a 40 A MAXI</text>

    <!-- K1A -->
    <line x1="1040" y1="260" x2="1040" y2="290" stroke="#D92D20" stroke-width="4" marker-end="url(#arrowRed)" />
    <rect x="940" y="290" width="200" height="65" rx="8" fill="#FEE4E2" stroke="#D92D20" stroke-width="2" filter="url(#boxShadow)" />
    <text x="1040" y="315" text-anchor="middle" font-size="14" font-weight="700" fill="#B42318">K1 (Contato K1A)</text>
    <text x="1040" y="333" text-anchor="middle" font-size="12" font-weight="600" fill="#344054">Contato de Potencia Esq.</text>
    <text x="1040" y="347" text-anchor="middle" font-size="10" font-weight="700" fill="#D92D20">Abertura Imediata por SR-01</text>

    <!-- MC-01 (Spark MAX) -->
    <line x1="1040" y1="355" x2="1040" y2="400" stroke="#D92D20" stroke-width="4" marker-end="url(#arrowRed)" />
    <rect x="935" y="400" width="210" height="85" rx="8" fill="#D1FADF" stroke="#12B76A" stroke-width="2" filter="url(#boxShadow)" />
    <text x="1040" y="427" text-anchor="middle" font-size="15" font-weight="700" fill="#027A48">MC-01 (Spark MAX)</text>
    <text x="1040" y="447" text-anchor="middle" font-size="12" font-weight="600" fill="#344054">Driver REV Spark MAX Esq.</text>
    <text x="1040" y="463" text-anchor="middle" font-size="11" font-weight="500" fill="#475467">PWM / CAN • In: 12V / 0V</text>
    <text x="1040" y="477" text-anchor="middle" font-size="10" font-weight="700" fill="#B42318">+12V VMOT (10-12 AWG)</text>

    <!-- MOT-01 (CIM) -->
    <line x1="1040" y1="485" x2="1040" y2="535" stroke="#12B76A" stroke-width="3" marker-end="url(#arrowGreen)" />
    <rect x="935" y="535" width="210" height="80" rx="8" fill="#F2F4F7" stroke="#475467" stroke-width="2" filter="url(#boxShadow)" />
    <text x="1040" y="562" text-anchor="middle" font-size="15" font-weight="700" fill="#1D2939">MOT-01 (Motor CIM)</text>
    <text x="1040" y="582" text-anchor="middle" font-size="12" font-weight="600" fill="#344054">Motor AndyMark CIM Esq.</text>
    <text x="1040" y="598" text-anchor="middle" font-size="10" font-weight="500" fill="#475467">12V DC • 5310 RPM • 133A Stall</text>

    <!-- CANAL MOTOR DIREITO -->
    <!-- F03 -->
    <line x1="1430" y1="140" x2="1430" y2="210" stroke="#D92D20" stroke-width="4" marker-end="url(#arrowRed)" />
    <rect x="1330" y="210" width="200" height="50" rx="6" fill="#FEF0C7" stroke="#DC6803" stroke-width="2" filter="url(#boxShadow)" />
    <text x="1430" y="230" text-anchor="middle" font-size="13" font-weight="700" fill="#B54708">F03 (Motor Direito)</text>
    <text x="1430" y="247" text-anchor="middle" font-size="11" font-weight="700" fill="#B42318">30 A a 40 A MAXI</text>

    <!-- K1B -->
    <line x1="1430" y1="260" x2="1430" y2="290" stroke="#D92D20" stroke-width="4" marker-end="url(#arrowRed)" />
    <rect x="1330" y="290" width="200" height="65" rx="8" fill="#FEE4E2" stroke="#D92D20" stroke-width="2" filter="url(#boxShadow)" />
    <text x="1430" y="315" text-anchor="middle" font-size="14" font-weight="700" fill="#B42318">K1 (Contato K1B)</text>
    <text x="1430" y="333" text-anchor="middle" font-size="12" font-weight="600" fill="#344054">Contato de Potencia Dir.</text>
    <text x="1430" y="347" text-anchor="middle" font-size="10" font-weight="700" fill="#D92D20">Abertura Imediata por SR-01</text>

    <!-- MC-02 (Spark MAX) -->
    <line x1="1430" y1="355" x2="1430" y2="400" stroke="#D92D20" stroke-width="4" marker-end="url(#arrowRed)" />
    <rect x="1325" y="400" width="210" height="85" rx="8" fill="#D1FADF" stroke="#12B76A" stroke-width="2" filter="url(#boxShadow)" />
    <text x="1430" y="427" text-anchor="middle" font-size="15" font-weight="700" fill="#027A48">MC-02 (Spark MAX)</text>
    <text x="1430" y="447" text-anchor="middle" font-size="12" font-weight="600" fill="#344054">Driver REV Spark MAX Dir.</text>
    <text x="1430" y="463" text-anchor="middle" font-size="11" font-weight="500" fill="#475467">PWM / CAN • In: 12V / 0V</text>
    <text x="1430" y="477" text-anchor="middle" font-size="10" font-weight="700" fill="#B42318">+12V VMOT (10-12 AWG)</text>

    <!-- MOT-02 (CIM) -->
    <line x1="1430" y1="485" x2="1430" y2="535" stroke="#12B76A" stroke-width="3" marker-end="url(#arrowGreen)" />
    <rect x="1325" y="535" width="210" height="80" rx="8" fill="#F2F4F7" stroke="#475467" stroke-width="2" filter="url(#boxShadow)" />
    <text x="1430" y="562" text-anchor="middle" font-size="15" font-weight="700" fill="#1D2939">MOT-02 (Motor CIM)</text>
    <text x="1430" y="582" text-anchor="middle" font-size="12" font-weight="600" fill="#344054">Motor AndyMark CIM Dir.</text>
    <text x="1430" y="598" text-anchor="middle" font-size="10" font-weight="500" fill="#475467">12V DC • 5310 RPM • 133A Stall</text>

    <!-- Retornos 0V GND dos Spark MAX -->
    <path d="M 1120 485 L 1120 795" fill="none" stroke="#1D2939" stroke-width="4" marker-end="url(#arrowDark)" />
    <text x="1125" y="720" font-size="10" font-weight="700" fill="#1D2939">MC-01 GND (10-12 AWG)</text>

    <path d="M 1510 485 L 1510 795" fill="none" stroke="#1D2939" stroke-width="4" marker-end="url(#arrowDark)" />
    <text x="1515" y="720" font-size="10" font-weight="700" fill="#1D2939">MC-02 GND (10-12 AWG)</text>
  </g>

  <!-- LINHAS TRACEJADAS DE INTERTRAVAMENTO DE SEGURANCA -->
  <!-- SR-01 -> K1A -->
  <path d="M 305 700 L 330 700 L 330 322 L 940 322" fill="none" stroke="#D92D20" stroke-width="2" stroke-dasharray="6,4" marker-end="url(#arrowRed)" />
  <text x="635" y="315" text-anchor="middle" font-size="11" font-weight="700" fill="#D92D20">Comanda abertura K1A (Corte Potencia)</text>

  <!-- SR-01 -> K1B -->
  <path d="M 305 720 L 320 720 L 320 340 L 1260 340 L 1260 322 L 1330 322" fill="none" stroke="#D92D20" stroke-width="2" stroke-dasharray="6,4" marker-end="url(#arrowRed)" />
  <text x="1135" y="333" text-anchor="middle" font-size="11" font-weight="700" fill="#D92D20">Comanda abertura K1B (Corte Potencia)</text>

  <!-- EMG-01 Contato Auxiliar -> ESP32 (GPIO 34) -->
  <path d="M 305 600 L 340 600 L 340 550 L 390 550" fill="none" stroke="#444CE7" stroke-width="2" stroke-dasharray="5,4" marker-end="url(#arrowBlue)" />
  <text x="345" y="575" text-anchor="middle" font-size="10" font-weight="700" fill="#3538CD">Aux E-Stop -&gt; GPIO 34</text>

  <!-- NOTAS DE ENGENHARIA NO RODAPE -->
  <rect x="40" y="855" width="1520" height="135" rx="8" fill="#F8F9FA" stroke="#D0D5DD" stroke-width="1.5" />
  <text x="60" y="880" font-size="13" font-weight="700" fill="#1D2939">DIMENSIONAMENTO TECNICO E NOTAS DE ENGENHARIA ELETRICA (CONFORME NR-12 E IEC 60204-1):</text>

  <text x="60" y="905" font-size="12" font-weight="700" fill="#B42318">• Barramento Principal (+12V e 0V):</text>
  <text x="310" y="905" font-size="12" font-weight="400" fill="#344054">Condutores de cobre flexivel de alta pureza bitola 4 AWG (capacidade nominal &gt; 100A continuos, suporta picos de ate 130A dos motores CIM).</text>

  <text x="60" y="928" font-size="12" font-weight="700" fill="#B54708">• Fusiveis dos Motores F02 e F03:</text>
  <text x="310" y="928" font-size="12" font-weight="400" fill="#344054">Recomendado fusiveis automotivos MAXI de 30 A a 40 A ou disjuntores termicos Snap Action para protecao contra travamento de rotor.</text>

  <text x="60" y="951" font-size="12" font-weight="700" fill="#027A48">• Circuito Fail-Safe de Emergencia:</text>
  <text x="310" y="951" font-size="12" font-weight="400" fill="#344054">O contator K1 e desenergizado ativamente ao abrir EMG-01, cortando fisicamente a linha VMOT dos Spark MAX sem depender de software.</text>

  <text x="60" y="974" font-size="12" font-weight="700" fill="#026AA2">• Alimentacao Logica Protegida (5.1V):</text>
  <text x="310" y="974" font-size="12" font-weight="400" fill="#344054">Conversor DC-01 dedicado de 5,1V / 5A mantém a Raspberry Pi 3B e ESP32 livres de brownouts causados pela partida dos motores.</text>
</svg>'''
    return svg

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'docs', 'hardware'))
    os.makedirs(base_dir, exist_ok=True)

    drawio_file = os.path.join(base_dir, 'circuito_potencia_agv.drawio')
    svg_file = os.path.join(base_dir, 'circuito_potencia_agv.svg')

    drawio_content = get_drawio_xml()
    # Validate XML
    ET.fromstring(drawio_content)
    with open(drawio_file, 'w', encoding='utf-8') as f:
        f.write(drawio_content)
    print(f"Sucesso: {drawio_file}")

    svg_content = get_svg()
    # Validate SVG XML
    ET.fromstring(svg_content)
    with open(svg_file, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print(f"Sucesso: {svg_file}")

if __name__ == '__main__':
    main()
