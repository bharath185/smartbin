def stepActive(st):
    if st=='ASSIGNED': return 2
    if st=='IN_PROGRESS': return 3
    return 1
def isActiveStatus(st): return st in ('OPEN','UNDER_REVIEW','ASSIGNED','IN_PROGRESS')
def isResolved(st): return st in ('RESOLVED','CLOSED')
def compactTL(st):
    active=-1 if isResolved(st) else stepActive(st)
    print(' ', st, 'active=',active,'->',end=' ')
    for i in range(5):
        done = isResolved(st) or i<active
        cur = (not isResolved(st)) and i==active
        print('D' if done else ('A' if cur else '.'),end='')
    print()
for st in ['OPEN','UNDER_REVIEW','ASSIGNED','IN_PROGRESS','RESOLVED']:
    compactTL(st)
# active first ordering
mine=[dict(ref=105,status='RESOLVED',created='2026-09-02'),dict(ref=108,status='IN_PROGRESS',created='2026-09-01'),dict(ref=102,status='OPEN',created='2026-09-03')]
def sortall(filter,sort):
    list=mine[:]
    if filter=='all' and sort=='new':
        list.sort(key=lambda a:(1 if isResolved(a['status']) else 0,a['created']))
    return list
print('Active-first order:',[x['ref'] for x in sortall('all','new')])
