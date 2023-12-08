import fileinput

with open(r'lens2-helm/Chart.yaml', 'r') as chart:
    data = chart.readlines()
    num = -1
    for line in data:
        line = line.replace('\n','')
        num = num + 1
        if 'version:' in line:
            version = line
            ver = line.split('.')
            ver[1] = str(int(ver[1]) + 1)
            new_ver = '.'.join(ver)
            new_ver = new_ver + '\n'
            data[num] = line.replace(version, new_ver)

with open('lens2-helm/Chart.yaml', 'w') as chart:
    chart.write(''.join(data))