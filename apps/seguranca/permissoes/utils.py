"""
Utilitários para verificação de permissões/acessos.
"""
from django.contrib.auth.models import User
from apps.seguranca.permissoes.models import Acesso, ControleAcessos, AcessoHierarquia

def user_has_any_access(user: User, codes: list) -> bool:
    """Verifica se o usuário tem acesso a pelo menos um dos códigos."""
    return any(user_has_access(user, c) for c in codes)

def user_has_access(user: User, code: str) -> bool:
    """
    Verifica se o usuário tem acesso ao código fornecido.
    
    IMPORTANTE: Superusers têm acesso total a tudo, não precisam de permissões específicas.
    
    Retorna True se:
    - user.is_superuser (SUPERUSERS SEMPRE TÊM ACESSO)
    - usuário autenticado e possui o acesso no formato <TIPO><ID> (ex: CT1, SCT5)
    
    Args:
        user: Usuário Django
        code: Código de acesso no formato TIPO + ID (ex: 'CT1', 'SCT5', 'SS10')
    
    Returns:
        bool: True se o usuário tem acesso, False caso contrário
    """
    print(f"[DEBUG] user_has_access chamado: user={user.username if user else 'None'}, code={code}")
    
    if not user or not user.is_authenticated:
        print(f"[DEBUG] Usuário não autenticado ou None")
        return False
    
    # SUPERUSERS SEMPRE TÊM ACESSO TOTAL - não precisa verificar permissões
    if user.is_superuser:
        print(f"[DEBUG] Usuário é superuser, retornando True")
        return True

    # Extrai tipo e id do código, testando prefixos mais longos primeiro
    tipos = sorted([t for t, _ in Acesso.TIPO_CHOICES], key=len, reverse=True)
    acesso_id = None
    tipo_code = None

    for tipo in tipos:
        if code.startswith(tipo):
            try:
                acesso_id = int(code[len(tipo):])
                tipo_code = tipo
                break
            except ValueError:
                print(f"[DEBUG] Erro ao converter ID do código {code}")
                return False

    if acesso_id is None or tipo_code is None:
        print(f"[DEBUG] Não foi possível extrair tipo e ID do código: {code}")
        return False
    
    print(f"[DEBUG] Código extraído: tipo={tipo_code}, id={acesso_id}")

    # Verifica se o Acesso existe e está ativo
    acesso_exists = Acesso.objects.filter(
        id=acesso_id, 
        tipo=tipo_code, 
        status=True
    ).exists()
    
    if not acesso_exists:
        print(f"[DEBUG] Acesso {tipo_code}{acesso_id} não existe ou está inativo")
        return False
    
    print(f"[DEBUG] Acesso {tipo_code}{acesso_id} existe e está ativo")

    # Verifica se o usuário tem esse acesso no ControleAcessos
    try:
        controle = ControleAcessos.objects.filter(
            user=user,
            status=True
        ).prefetch_related('acessos').first()
        
        if not controle:
            print(f"[DEBUG] Usuário {user.username} não tem ControleAcessos ativo")
            return False
        
        # Verifica diretamente na lista de acessos já carregada
        acessos_usuario = list(controle.acessos.filter(status=True))
        acessos_ids_usuario = [a.id for a in acessos_usuario]
        acessos_codigos_usuario = [f"{a.tipo}{a.id}" for a in acessos_usuario]
        acessos_detalhados = [f"{a.tipo}{a.id} (id={a.id}, nome={a.nome})" for a in acessos_usuario]
        
        print(f"[DEBUG] Usuário {user.username} tem {len(acessos_usuario)} acessos:")
        for acesso_det in acessos_detalhados:
            print(f"[DEBUG]   - {acesso_det}")
        print(f"[DEBUG] Verificando se usuário tem acesso a: {tipo_code}{acesso_id} (id={acesso_id})")
        print(f"[DEBUG] IDs dos acessos do usuário: {acessos_ids_usuario}")
        print(f"[DEBUG] O acesso desejado (id={acesso_id}) está na lista? {acesso_id in acessos_ids_usuario}")
        
        # Verifica se tem o acesso direto
        for acesso in acessos_usuario:
            if acesso.id == acesso_id and acesso.tipo == tipo_code:
                print(f"[DEBUG] Usuário tem acesso DIRETO a {tipo_code}{acesso_id}")
                return True
        
        print(f"[DEBUG] Usuário NÃO tem acesso direto a {tipo_code}{acesso_id}, verificando hierarquia...")
        
        # Se não tem acesso direto, verifica hierarquia em duas direções:
        # 1. Se o acesso desejado é pai de algum acesso do usuário (direto)
        # 2. Se algum acesso do usuário é filho do acesso desejado (através de hierarquias)
        
        acesso_desejado = Acesso.objects.filter(id=acesso_id, tipo=tipo_code, status=True).first()
        if not acesso_desejado:
            print(f"[DEBUG] Acesso desejado {tipo_code}{acesso_id} não encontrado")
            return False
        
        # DIREÇÃO 1: Verifica se o acesso desejado é pai de algum acesso do usuário
        # (ou seja, o acesso desejado é pai de algum acesso que o usuário tem)
        hierarquias_pai = AcessoHierarquia.objects.filter(
            pai=acesso_desejado,
            status=True
        ).prefetch_related('filhos').all()
        
        print(f"[DEBUG] Verificando {hierarquias_pai.count()} hierarquias onde {tipo_code}{acesso_id} é pai")
        
        for hierarquia in hierarquias_pai:
            filhos_ids = list(hierarquia.filhos.filter(status=True).values_list('id', flat=True))
            filhos_codigos = [f"{Acesso.objects.get(id=fid).tipo}{fid}" for fid in filhos_ids]
            print(f"[DEBUG] Hierarquia: {tipo_code}{acesso_id} tem filhos: {filhos_codigos}")
            # Se o usuário tem algum filho deste pai, ele tem acesso ao pai
            if any(filho_id in acessos_ids_usuario for filho_id in filhos_ids):
                print(f"[DEBUG] Usuário tem acesso HIERÁRQUICO (direção 1) a {tipo_code}{acesso_id} (tem filho)")
                return True
        
        # DIREÇÃO 2: Verifica se algum acesso do usuário é filho do acesso desejado
        # (ou seja, verifica hierarquias onde algum acesso do usuário aparece como filho)
        print(f"[DEBUG] Verificando hierarquias onde acessos do usuário são filhos de {tipo_code}{acesso_id}")
        
        for acesso_usuario in acessos_usuario:
            # Busca hierarquias onde este acesso do usuário é filho
            hierarquias_filho = AcessoHierarquia.objects.filter(
                filhos=acesso_usuario,
                status=True
            ).prefetch_related('pai').all()
            
            for hierarquia in hierarquias_filho:
                pai = hierarquia.pai
                # Se o pai desta hierarquia é o acesso desejado, o usuário tem acesso
                if pai.id == acesso_id and pai.tipo == tipo_code and pai.status:
                    print(f"[DEBUG] Usuário tem acesso HIERÁRQUICO (direção 2) a {tipo_code}{acesso_id} (seu acesso {acesso_usuario.tipo}{acesso_usuario.id} é filho)")
                    return True
                
                # Verifica recursivamente: se o pai também tem um pai que é o acesso desejado
                # (ex: SS14 -> SCT6 -> CT1)
                hierarquias_pai_pai = AcessoHierarquia.objects.filter(
                    filhos=pai,
                    status=True
                ).prefetch_related('pai').all()
                
                for hier_pai_pai in hierarquias_pai_pai:
                    pai_pai = hier_pai_pai.pai
                    if pai_pai.id == acesso_id and pai_pai.tipo == tipo_code and pai_pai.status:
                        print(f"[DEBUG] Usuário tem acesso HIERÁRQUICO (direção 2 recursivo) a {tipo_code}{acesso_id} (seu acesso {acesso_usuario.tipo}{acesso_usuario.id} é neto)")
                        return True
        
        print(f"[DEBUG] Usuário NÃO tem acesso (nem direto nem hierárquico) a {tipo_code}{acesso_id}")
        return False
    except Exception:
        # Em caso de erro, tenta método alternativo
        try:
            # Verifica acesso direto
            if ControleAcessos.objects.filter(
                user=user,
                status=True,
                acessos__id=acesso_id,
                acessos__tipo=tipo_code,
                acessos__status=True
            ).exists():
                return True
            
            # Verifica hierarquia (se tem filho, tem acesso ao pai)
            acesso_desejado = Acesso.objects.filter(id=acesso_id, tipo=tipo_code, status=True).first()
            if acesso_desejado:
                # Busca hierarquias onde o acesso desejado é pai
                hierarquias = AcessoHierarquia.objects.filter(
                    pai=acesso_desejado,
                    status=True
                ).prefetch_related('filhos')
                
                for hierarquia in hierarquias:
                    filhos_ids = list(hierarquia.filhos.filter(status=True).values_list('id', flat=True))
                    # Se o usuário tem algum filho, tem acesso ao pai
                    if filhos_ids and ControleAcessos.objects.filter(
                        user=user,
                        status=True,
                        acessos__id__in=filhos_ids
                    ).exists():
                        return True
            
            return False
        except Exception:
            return False

