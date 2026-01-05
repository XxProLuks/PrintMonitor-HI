# Script PowerShell para listar impressoras da rede
# Gera um arquivo JSON com as impressoras encontradas

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ("="*70)
Write-Host "LISTANDO IMPRESSORAS DA REDE"
Write-Host ("="*70)
Write-Host ""

$ErrorActionPreference = 'Stop'

try {
    # Lista impressoras de rede
    Write-Host "Buscando impressoras de rede..."
    $printers = Get-Printer | Where-Object { 
        $_.Network -eq $true -or 
        $_.PortName -like '*.*' -or
        $_.PortName -like 'IP_*' -or
        $_.PortName -like 'WSD*' -or
        $_.PortName -like 'TCPIP_*'
    } | Select-Object Name, PortName, DriverName, Location, Network, Shared
    
    if ($printers) {
        Write-Host "   [OK] Encontradas $($printers.Count) impressoras"
        Write-Host ""
        
        # Extrai IPs das portas
        $printers_with_ip = @()
        foreach ($printer in $printers) {
            $ip = $null
            $portName = $printer.PortName
            
            if ($portName) {
                # Tenta extrair IP da porta
                if ($portName -match '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}') {
                    $ip = $matches[0]
                } elseif ($portName -like 'IP_*' -or $portName -like 'TCPIP_*') {
                    $parts = $portName -split '_'
                    foreach ($part in $parts) {
                        if ($part -match '^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$') {
                            $ip = $part
                            break
                        }
                    }
                }
            }
            
            # Se não encontrou IP na porta, tenta extrair da Location (URL)
            if (-not $ip -and $printer.Location) {
                $location = $printer.Location
                # Tenta extrair IP de URLs como http://192.168.1.100:8080
                if ($location -match 'http[s]?://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})') {
                    $ip = $matches[1]
                }
            }
            
            # Se ainda não encontrou, tenta resolver o nome da impressora como hostname
            if (-not $ip -and $printer.Name) {
                try {
                    $resolved = [System.Net.Dns]::GetHostAddresses($printer.Name) | Where-Object { 
                        $_.AddressFamily -eq 'InterNetwork' -and -not $_.IsIPv6LinkLocal 
                    } | Select-Object -First 1
                    if ($resolved) {
                        $ip = $resolved.IPAddressToString
                    }
                } catch {
                    # Ignora erros de resolução
                }
            }
            
            $printers_with_ip += [PSCustomObject]@{
                Name = $printer.Name
                IP = $ip
                PortName = $portName
                DriverName = $printer.DriverName
                Location = $printer.Location
                Network = $printer.Network
                Shared = $printer.Shared
            }
        }
        
        # Exibe lista formatada
        Write-Host "IMPRESSORAS ENCONTRADAS:"
        Write-Host ""
        $printers_with_ip | Format-Table -AutoSize
        
        # Gera JSON
        $json = $printers_with_ip | ConvertTo-Json -Depth 2
        $outputFile = "impressoras_rede.json"
        $json | Out-File -FilePath $outputFile -Encoding UTF8
        
        Write-Host ""
        Write-Host ("="*70)
        Write-Host "[OK] Lista salva em: $outputFile"
        Write-Host ""
        Write-Host "PROXIMOS PASSOS:"
        Write-Host "   1. Abra o arquivo impressoras_rede.json"
        Write-Host "   2. Copie os dados para cadastrar_impressoras_manual.py"
        Write-Host "   3. Execute: python cadastrar_impressoras_manual.py"
        Write-Host ("="*70)
        
        # Também gera um arquivo CSV para facilitar
        $csvFile = "impressoras_rede.csv"
        $printers_with_ip | Export-Csv -Path $csvFile -NoTypeInformation -Encoding UTF8
        Write-Host "   CSV tambem salvo em: $csvFile"
        Write-Host ""
        
    } else {
        Write-Host "   [AVISO] Nenhuma impressora de rede encontrada"
        Write-Host ""
        Write-Host "DICAS:"
        Write-Host "   - Verifique se as impressoras estao instaladas no Windows"
        Write-Host "   - Tente executar: Get-Printer | Format-Table"
        Write-Host "   - Use o cadastro manual se necessario"
    }
    
} catch {
    Write-Host "ERRO: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Tente executar como Administrador"
    exit 1
}

