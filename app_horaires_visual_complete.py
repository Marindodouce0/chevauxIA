import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta
import base64
from io import BytesIO

# Configuration de la page
st.set_page_config(
    page_title="Planificateur d'Horaires Équestres",
    page_icon="🐴",
    layout="wide"
)

# CSS pour le calendrier visuel
st.markdown("""
<style>
    .calendar-container {
        overflow-x: auto;
        margin: 20px 0;
    }
    .calendar-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 12px;
        background-color: white;
    }
    .calendar-table th {
        background-color: #2e7d32;
        color: white;
        padding: 12px;
        text-align: center;
        position: sticky;
        top: 0;
        font-weight: bold;
        font-size: 14px;
        letter-spacing: 0.5px;
        z-index: 20;
    }
    .calendar-table td {
        border: 1px solid #ddd;
        padding: 8px;
        vertical-align: top;
        min-width: 120px;
    }
    .calendar-table tbody tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    .calendar-table tbody tr:hover {
        background-color: #f0f0f0;
    }
    .time-header {
        background-color: #37474f;
        color: white;
        font-weight: bold;
        width: 120px;
        text-align: center;
        position: sticky;
        left: 0;
        font-size: 14px;
        letter-spacing: 0.5px;
        border-right: 2px solid #263238;
        box-shadow: 2px 0 4px rgba(0,0,0,0.1);
        z-index: 10;
    }
    th.time-header {
        z-index: 30;
        background-color: #1b5e20 !important;
    }
    tr:hover .time-header {
        background-color: #263238;
        transform: scale(1.02);
        transition: all 0.2s ease;
    }
    .course-block {
        border-radius: 5px;
        padding: 8px;
        margin: 2px;
        font-size: 12px;
        line-height: 1.4;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .course-active {
        background-color: #e3f2fd;
        border-left: 4px solid #1976d2;
        color: #0d47a1;
    }
    .course-active strong {
        color: #1565c0;
    }
    .course-passive {
        background-color: #e8f5e9;
        border-left: 4px solid #388e3c;
        color: #1b5e20;
    }
    .course-passive strong {
        color: #2e7d32;
    }
    .mise-liberte {
        background-color: #fff8e1;
        border-left: 4px solid #f57c00;
        color: #e65100;
    }
    .mise-liberte strong {
        color: #ef6c00;
    }
    .conflict-warning {
        background-color: #ffcdd2;
        color: #c62828;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .stats-card {
        background-color: #f5f5f5;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stats-number {
        font-size: 2.5em;
        font-weight: bold;
        color: #2e7d32;
    }
</style>
""", unsafe_allow_html=True)

# Fonctions utilitaires pour la visualisation
def get_activity_style(activity_type):
    """Retourner la classe CSS selon le type d'activité"""
    styles = {
        'Cours Actif': 'course-active',
        'Cours Passif': 'course-passive',
        'Mise en liberté': 'mise-liberte'
    }
    return styles.get(activity_type, '')

def create_weekly_schedule_html(schedule, type_activite, jours_actifs):
    """Créer un emploi du temps hebdomadaire pour un type d'activité"""
    
    # Collecter toutes les activités par jour et heure
    weekly_data = {}
    for jour in jours_actifs:
        weekly_data[jour] = {}
        
        for cheval, planning in schedule.items():
            if jour in planning:
                for activity in planning[jour]:
                    if activity['type'] == type_activite:
                        time_key = f"{activity['heure_debut'].strftime('%H:%M')}-{activity['heure_fin'].strftime('%H:%M')}"
                        nom_activite = activity['nom']
                        
                        # Pour les cours, utiliser le nom normalisé si disponible
                        if type_activite == 'Cours Actif' and 'nom_norm' in activity:
                            # Grouper par nom normalisé
                            group_key = activity['nom_norm']
                        else:
                            group_key = nom_activite
                        
                        key = f"{time_key}||{group_key}"
                        
                        if key not in weekly_data[jour]:
                            weekly_data[jour][key] = {
                                'nom': nom_activite,
                                'chevaux': [],
                                'heure_debut': activity['heure_debut'],
                                'heure_fin': activity['heure_fin'],
                                'time_key': time_key
                            }
                        
                        weekly_data[jour][key]['chevaux'].append(cheval)
    
    # Obtenir toutes les plages horaires uniques
    all_time_slots = set()
    for jour_data in weekly_data.values():
        for key in jour_data.keys():
            time_part = key.split('||')[0]
            all_time_slots.add(time_part)
    
    if not all_time_slots:
        return "<p>Aucune activité de ce type cette semaine.</p>"
    
    # Trier les créneaux horaires
    sorted_slots = sorted(all_time_slots, key=lambda x: x.split('-')[0])
    
    # Créer le HTML
    style_class = get_activity_style(type_activite)
    
    html = '<div class="calendar-container">'
    html += '<table class="calendar-table">'
    
    # En-tête avec les jours
    html += '<thead><tr>'
    html += '<th class="time-header">Heures</th>'
    for jour in jours_actifs:
        html += f'<th style="text-align: center; min-width: 180px;">{jour}</th>'
    html += '</tr></thead>'
    
    # Corps du tableau
    html += '<tbody>'
    
    for time_slot in sorted_slots:
        html += '<tr>'
        html += f'<td class="time-header">{time_slot}</td>'
        
        for jour in jours_actifs:
            # Trouver toutes les activités pour ce créneau
            activities_in_slot = []
            for key, data in weekly_data[jour].items():
                if data['time_key'] == time_slot:
                    activities_in_slot.append(data)
            
            if activities_in_slot:
                html += f'<td class="course-block {style_class}">'
                for data in activities_in_slot:
                    html += f'<strong>{data["nom"]}</strong><br>'
                    # Trier les chevaux et les afficher
                    chevaux_sorted = sorted(data["chevaux"])
                    html += f'<span style="font-weight: 600; color: #333;">({len(chevaux_sorted)} chevaux)</span><br>'
                    html += f'<small style="color: #555;">{", ".join(chevaux_sorted)}</small><br><br>'
                html = html.rstrip('<br><br>')  # Enlever les derniers <br>
                html += '</td>'
            else:
                html += '<td></td>'
        
        html += '</tr>'
    
    html += '</tbody></table></div>'
    
    return html

def create_park_weekly_schedule_html(schedule, jours_actifs):
    """Créer un emploi du temps hebdomadaire pour les parcs de mise en liberté"""
    
    # Collecter toutes les mises en liberté par jour et heure
    weekly_parks = {}
    for jour in jours_actifs:
        weekly_parks[jour] = {}
        
        for cheval, planning in schedule.items():
            if jour in planning:
                for activity in planning[jour]:
                    if activity['type'] == 'Mise en liberté':
                        time_key = activity['heure_debut'].strftime('%H:%M')
                        park = activity.get('parc', 'Parc ?')
                        
                        if time_key not in weekly_parks[jour]:
                            weekly_parks[jour][time_key] = {}
                        
                        if park not in weekly_parks[jour][time_key]:
                            weekly_parks[jour][time_key][park] = []
                        
                        weekly_parks[jour][time_key][park].append(cheval)
    
    # Obtenir toutes les heures uniques
    all_times = set()
    for jour_data in weekly_parks.values():
        all_times.update(jour_data.keys())
    
    if not all_times:
        return "<p>Aucune mise en liberté cette semaine.</p>"
    
    sorted_times = sorted(all_times)
    
    # Créer le HTML
    html = '<div class="calendar-container">'
    html += '<table class="calendar-table">'
    
    # En-tête
    html += '<thead><tr>'
    html += '<th class="time-header">Heures</th>'
    for jour in jours_actifs:
        html += f'<th style="text-align: center;">{jour}</th>'
    html += '</tr></thead>'
    
    # Corps
    html += '<tbody>'
    
    for time_slot in sorted_times:
        html += '<tr>'
        html += f'<td class="time-header">{time_slot}</td>'
        
        for jour in jours_actifs:
            if time_slot in weekly_parks[jour]:
                html += '<td class="course-block mise-liberte">'
                # Trier les parcs
                for park in sorted(weekly_parks[jour][time_slot].keys()):
                    chevaux = sorted(weekly_parks[jour][time_slot][park])
                    html += f'<strong style="color: #e65100;">{park}:</strong><br>'
                    html += f'<small style="color: #555;">({len(chevaux)}) {", ".join(chevaux)}</small><br><br>'
                html = html.rstrip('<br><br>')
                html += '</td>'
            else:
                html += '<td></td>'
        
        html += '</tr>'
    
    html += '</tbody></table></div>'
    
    return html

# En-tête principal
st.markdown("""
<div style='text-align: center; padding: 20px; background: linear-gradient(135deg, #2e7d32 0%, #66bb6a 100%); 
            color: white; border-radius: 10px; margin-bottom: 30px;'>
    <h1 style='margin: 0;'>🐴 Planificateur d'Horaires Équestres</h1>
    <p style='margin: 10px 0 0 0; opacity: 0.9;'>Version avec visualisation améliorée</p>
</div>
""", unsafe_allow_html=True)

# Initialiser l'état
if 'schedule' not in st.session_state:
    st.session_state.schedule = None
if 'horaires_generes' not in st.session_state:
    st.session_state.horaires_generes = False

# Barre latérale pour la configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    st.subheader("🐎 Chevaux solos")
    chevaux_solos_text = st.text_area(
        "Un cheval par ligne:",
        value="Mykola\nManhattan\nBully",
        height=100
    )
    CHEVAUX_SOLOS = [c.strip() for c in chevaux_solos_text.split('\n') if c.strip()]
    
    st.subheader("📅 Jours actifs")
    JOURS_SEMAINE = st.multiselect(
        "Sélectionner les jours:",
        ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'],
        default=['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
    )

# Onglets principaux
tab1, tab2, tab3, tab4 = st.tabs([
    "📁 Import des données", 
    "🔄 Génération", 
    "📊 Visualisation des horaires", 
    "📥 Export"
])

# TAB 1: Import
with tab1:
    st.header("Import des fichiers CSV")
    
    with st.expander("📖 Instructions", expanded=True):
        st.info("""
        **Fichiers requis:**
        1. **BD_chevaux.csv** - Liste des chevaux
        2. **BD_competences_chevaux.csv** - Compétences
        3. **BD_cours_manège.csv** - Cours actifs
        4. **BD_cours_autres.csv** - Cours passifs
        5. **BD_amis_long.csv** - Relations d'amitié
        """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        file_chevaux = st.file_uploader("BD_chevaux.csv", type=['csv'], key='chevaux')
        file_competences = st.file_uploader("BD_competences_chevaux.csv", type=['csv'], key='competences')
        file_amis = st.file_uploader("BD_amis_long.csv", type=['csv'], key='amis')
    
    with col2:
        file_cours_manege = st.file_uploader("BD_cours_manège.csv", type=['csv'], key='manege')
        file_cours_autres = st.file_uploader("BD_cours_autres.csv", type=['csv'], key='autres')
    
    all_files_uploaded = all([file_chevaux, file_competences, file_cours_manege, file_cours_autres, file_amis])
    
    if all_files_uploaded:
        st.success("✅ Tous les fichiers ont été chargés!")

# TAB 2: Génération AVEC VOTRE CODE COMPLET
with tab2:
    st.header("Génération des horaires")
    
    if not all_files_uploaded:
        st.error("❌ Veuillez d'abord charger tous les fichiers dans l'onglet 'Import des données'")
    else:
        if st.button("🚀 Générer les horaires", type="primary", use_container_width=True):
            with st.spinner("Génération en cours... Cela peut prendre quelques secondes."):
                try:
                    # VOTRE CODE DE GÉNÉRATION COMPLET ICI
                    # --- ÉTAPE 1 & 2 : CHARGEMENT ET PRÉPARATION DES DONNÉES ---
                    df_chevaux = pd.read_csv(file_chevaux, sep=';')
                    df_competences = pd.read_csv(file_competences, sep=';')
                    df_cours_manege = pd.read_csv(file_cours_manege, sep=';')
                    df_cours_autres = pd.read_csv(file_cours_autres, sep=';')
                    df_amis = pd.read_csv(file_amis, sep=';')
                    
                    df_chevaux['Nom_Cheval'] = df_chevaux['Nom_Cheval'].str.strip()
                    df_competences['Nom_Cheval'] = df_competences['Nom_Cheval'].str.strip()
                    df_amis['Nom_Cheval'] = df_amis['Nom_Cheval'].str.strip()
                    df_amis['Amis'] = df_amis['Amis'].str.strip()
                    
                    for df in [df_cours_manege, df_cours_autres]:
                        df.dropna(subset=['Heure_début', 'Heure_fin'], inplace=True)
                        df['Heure_début'] = pd.to_datetime(df['Heure_début'], format='%H:%M', errors='coerce').dt.time
                        df['Heure_fin'] = pd.to_datetime(df['Heure_fin'], format='%H:%M', errors='coerce').dt.time
                    
                    df_cours_manege['Cours_nom_norm'] = df_cours_manege['Cours_nom'].str.lower()
                    competences_dict = {cheval.strip(): {} for cheval in df_chevaux['Nom_Cheval']}
                    for _, row in df_competences.iterrows(): 
                        competences_dict[row['Nom_Cheval']][row['Competence']] = row['Qualification']
                    amis_dict = {cheval.strip(): [] for cheval in df_chevaux['Nom_Cheval']}
                    for _, row in df_amis.iterrows():
                        if pd.notna(row['Amis']): 
                            amis_dict[row['Nom_Cheval']].append(row['Amis'])
                    liste_chevaux = df_chevaux['Nom_Cheval'].tolist()
                    work_hours = {cheval: {'active': 0.0, 'passive': 0.0} for cheval in liste_chevaux}
                    schedule = {cheval: {jour: [] for jour in JOURS_SEMAINE} for cheval in liste_chevaux}
                    conflits = []
                    
                    def est_cheval_disponible(cheval, jour, heure_debut, heure_fin, schedule):
                        for activite in schedule[cheval][jour]:
                            if activite['heure_debut'] < heure_fin and activite['heure_fin'] > heure_debut: 
                                return False
                        return True
                    
                    def calculer_duree(heure_debut, heure_fin):
                        dummy_date = datetime(2024, 1, 1)
                        dt_debut = datetime.combine(dummy_date, heure_debut)
                        dt_fin = datetime.combine(dummy_date, heure_fin)
                        if dt_fin < dt_debut: 
                            dt_fin += timedelta(days=1)
                        return (dt_fin - dt_debut).total_seconds() / 3600.0
                    
                    # Progress bar
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # --- Planification (1/3): Cours Actifs ---
                    status_text.text("Planification des cours actifs...")
                    progress_bar.progress(20)
                    
                    df_cours_manege_tries = df_cours_manege.sort_values(by=['Jour', 'Heure_début'])
                    for _, cours in df_cours_manege_tries.iterrows():
                        jour, hd, hf, comp, requis = cours['Jour'], cours['Heure_début'], cours['Heure_fin'], cours['Exigence_1'], cours['Nombre_chevaux']
                        if not all([isinstance(c, str) for c in [jour, comp]]) or pd.isna(requis): continue
                        if jour not in JOURS_SEMAINE: continue
                        candidats = [{'nom': nom, 'qualif': qualif} for nom in liste_chevaux if df_chevaux.loc[df_chevaux['Nom_Cheval'] == nom, 'Max_heures_Travail'].iloc[0] > 0 and est_cheval_disponible(nom, jour, hd, hf, schedule) and (qualif := competences_dict.get(nom, {}).get(comp, 'Non')) in ['Oui', 'Dépannage']]
                        candidats.sort(key=lambda c: (0 if c['qualif'] == 'Oui' else 1, work_hours[c['nom']]['active']))
                        selection = candidats[:int(requis)]
                        duree = calculer_duree(hd, hf)
                        for cheval in selection:
                            activite = {'type': 'Cours Actif', 'nom': cours['Cours_nom'], 'nom_norm': cours['Cours_nom_norm'], 'heure_debut': hd, 'heure_fin': hf}
                            schedule[cheval['nom']][jour].append(activite)
                            work_hours[cheval['nom']]['active'] += duree
                    
                    # --- Planification (2/3): Mises en Liberté ---
                    status_text.text("Planification des mises en liberté...")
                    progress_bar.progress(60)
                    
                    for jour in JOURS_SEMAINE:
                        chevaux_a_placer_ce_jour = set(liste_chevaux)
                        parcs_occupes = {p: [] for p in range(1, 10)}
                        parcs_etalon_occupes = {p: [] for p in range(1, 3)}
                        
                        # Traiter d'abord tous les chevaux solos
                        for cheval_nom in CHEVAUX_SOLOS:
                            if cheval_nom not in chevaux_a_placer_ce_jour:
                                continue
                                
                            creneaux_interdits = []
                            a_des_cours_apres_midi = False
                            for activite in schedule[cheval_nom][jour]:
                                if activite['type'] == 'Cours Actif':
                                    h_debut_cours, h_fin_cours = activite['heure_debut'], activite['heure_fin']
                                    if h_debut_cours >= time(12, 0): a_des_cours_apres_midi = True
                                    interdit_debut = (datetime.combine(datetime.min, h_debut_cours) - timedelta(hours=1)).time()
                                    interdit_fin = (datetime.combine(datetime.min, h_fin_cours) + timedelta(hours=1)).time()
                                    creneaux_interdits.append((interdit_debut, interdit_fin))
                            
                            plages_liberte_matin, plages_liberte_aprem = (time(7, 0), time(12, 0)), (time(13, 0), time(15, 30))
                            plages_liberte_ordonnees = [plages_liberte_matin, plages_liberte_aprem] if a_des_cours_apres_midi else [plages_liberte_aprem, plages_liberte_matin]
                            
                            creneau_trouve = False
                            for debut_plage, fin_plage in plages_liberte_ordonnees:
                                if creneau_trouve: break
                                heure_test = debut_plage
                                while heure_test <= fin_plage:
                                    hd_creneau, hf_creneau = heure_test, (datetime.combine(datetime.min, heure_test) + timedelta(hours=1)).time()
                                    if hf_creneau > fin_plage and hf_creneau.hour != 0: break
                                    
                                    if not any(hd_creneau < fin and hf_creneau > debut for debut, fin in creneaux_interdits):
                                        est_etalon_special = cheval_nom in ["Mykola", "Manhattan"]
                                        parc_a_utiliser = parcs_etalon_occupes if est_etalon_special else parcs_occupes
                                        
                                        parc_assigne = next((p for p, occs in parc_a_utiliser.items() 
                                                           if len([o for o in occs if hd_creneau < o['fin'] and hf_creneau > o['debut']]) == 0), None)
                                        
                                        if parc_assigne is not None:
                                            parc_nom = f"Parc E{parc_assigne}" if est_etalon_special else f"Parc {parc_assigne}"
                                            details = f"Sortie seul, {parc_nom}"
                                            schedule[cheval_nom][jour].append({
                                                'type': 'Mise en liberté', 
                                                'nom': details, 
                                                'parc': parc_nom, 
                                                'heure_debut': hd_creneau, 
                                                'heure_fin': hf_creneau
                                            })
                                            # IMPORTANT: Ajouter 2 occupations pour bloquer complètement le parc
                                            parc_a_utiliser[parc_assigne].extend([
                                                {'debut': hd_creneau, 'fin': hf_creneau},
                                                {'debut': hd_creneau, 'fin': hf_creneau}
                                            ])
                                            chevaux_a_placer_ce_jour.remove(cheval_nom)
                                            creneau_trouve = True
                                            break
                                    
                                    heure_test = (datetime.combine(datetime.min, heure_test) + timedelta(minutes=30)).time()
                            
                            if not creneau_trouve:
                                conflits.append(f"Mise en liberté impossible à placer pour {cheval_nom} (solo) le {jour}.")
                        
                        # Ensuite, traiter les autres chevaux
                        for cheval_nom in liste_chevaux:
                            if cheval_nom not in chevaux_a_placer_ce_jour: continue
                            if cheval_nom in CHEVAUX_SOLOS: continue
                                
                            creneaux_interdits = []
                            a_des_cours_apres_midi = False
                            for activite in schedule[cheval_nom][jour]:
                                if activite['type'] == 'Cours Actif':
                                    h_debut_cours, h_fin_cours = activite['heure_debut'], activite['heure_fin']
                                    if h_debut_cours >= time(12, 0): a_des_cours_apres_midi = True
                                    interdit_debut = (datetime.combine(datetime.min, h_debut_cours) - timedelta(hours=1)).time()
                                    interdit_fin = (datetime.combine(datetime.min, h_fin_cours) + timedelta(hours=1)).time()
                                    creneaux_interdits.append((interdit_debut, interdit_fin))
                            
                            plages_liberte_matin, plages_liberte_aprem = (time(7, 0), time(12, 0)), (time(13, 0), time(15, 30))
                            plages_liberte_ordonnees = [plages_liberte_matin, plages_liberte_aprem] if a_des_cours_apres_midi else [plages_liberte_aprem, plages_liberte_matin]
                            
                            creneau_trouve = False
                            for debut_plage, fin_plage in plages_liberte_ordonnees:
                                if creneau_trouve: break
                                heure_test = debut_plage
                                while heure_test <= fin_plage:
                                    hd_creneau, hf_creneau = heure_test, (datetime.combine(datetime.min, heure_test) + timedelta(hours=1)).time()
                                    if hf_creneau > fin_plage and hf_creneau.hour != 0: break
                                    
                                    if not any(hd_creneau < fin and hf_creneau > debut for debut, fin in creneaux_interdits):
                                        ami_trouve = None
                                        for ami_potentiel in amis_dict.get(cheval_nom, []):
                                            if (ami_potentiel in chevaux_a_placer_ce_jour and 
                                                ami_potentiel != cheval_nom and 
                                                ami_potentiel not in CHEVAUX_SOLOS and
                                                est_cheval_disponible(ami_potentiel, jour, hd_creneau, hf_creneau, schedule)):
                                                ami_trouve = ami_potentiel
                                                break
                                        
                                        if cheval_nom in ["Pepper", "Cooper"] and not ami_trouve: continue
                                        
                                        parc_a_utiliser = parcs_occupes
                                        parc_assigne = None
                                        
                                        if ami_trouve:
                                            parc_assigne = next((p for p, occs in parc_a_utiliser.items() 
                                                               if len([o for o in occs if hd_creneau < o['fin'] and hf_creneau > o['debut']]) == 0), None)
                                        else:
                                            parc_assigne = next((p for p, occs in parc_a_utiliser.items() 
                                                               if len([o for o in occs if hd_creneau < o['fin'] and hf_creneau > o['debut']]) < 2), None)
                                        
                                        if parc_assigne is not None:
                                            if ami_trouve:
                                                details, details_ami = f"avec {ami_trouve}, Parc {parc_assigne}", f"avec {cheval_nom}, Parc {parc_assigne}"
                                                schedule[cheval_nom][jour].append({
                                                    'type': 'Mise en liberté', 
                                                    'nom': details, 
                                                    'parc': f'Parc {parc_assigne}', 
                                                    'heure_debut': hd_creneau, 
                                                    'heure_fin': hf_creneau
                                                })
                                                schedule[ami_trouve][jour].append({
                                                    'type': 'Mise en liberté', 
                                                    'nom': details_ami, 
                                                    'parc': f'Parc {parc_assigne}', 
                                                    'heure_debut': hd_creneau, 
                                                    'heure_fin': hf_creneau
                                                })
                                                parc_a_utiliser[parc_assigne].extend([
                                                    {'debut': hd_creneau, 'fin': hf_creneau}, 
                                                    {'debut': hd_creneau, 'fin': hf_creneau}
                                                ])
                                                chevaux_a_placer_ce_jour.remove(cheval_nom)
                                                chevaux_a_placer_ce_jour.remove(ami_trouve)
                                            else:
                                                details = f"Sortie seul, Parc {parc_assigne}"
                                                schedule[cheval_nom][jour].append({
                                                    'type': 'Mise en liberté', 
                                                    'nom': details, 
                                                    'parc': f'Parc {parc_assigne}', 
                                                    'heure_debut': hd_creneau, 
                                                    'heure_fin': hf_creneau
                                                })
                                                parc_a_utiliser[parc_assigne].append({'debut': hd_creneau, 'fin': hf_creneau})
                                                chevaux_a_placer_ce_jour.remove(cheval_nom)
                                            creneau_trouve = True
                                            break
                                    
                                    heure_test = (datetime.combine(datetime.min, heure_test) + timedelta(minutes=30)).time()
                        
                        for cheval_restant in list(chevaux_a_placer_ce_jour):
                            conflits.append(f"Mise en liberté impossible à placer pour {cheval_restant} le {jour}.")
                    
                    # --- Planification (3/3): Cours Passifs ---
                    status_text.text("Planification des cours passifs...")
                    progress_bar.progress(80)
                    
                    df_cours_autres_tries = df_cours_autres.sort_values(by=['Jour', 'Heure_début'])
                    for _, cours in df_cours_autres_tries.iterrows():
                        jour, hd, hf, comp = cours['Jour'], cours['Heure_début'], cours['Heure_fin'], cours['Exigence']
                        requis = int(cours.get('Nombre_chevaux', 0))
                        if requis == 0 or pd.isna(comp) or jour not in JOURS_SEMAINE: continue
                        candidats = [{'nom': nom, 'qualif': qualif} for nom in liste_chevaux if est_cheval_disponible(nom, jour, hd, hf, schedule) and (qualif := competences_dict.get(nom, {}).get(comp, 'Non')) in ['Oui', 'Dépannage']]
                        candidats.sort(key=lambda c: (0 if c['qualif'] == 'Oui' else 1, work_hours[c['nom']]['active'] + work_hours[c['nom']]['passive']))
                        selection = candidats[:requis]
                        duree = calculer_duree(hd, hf)
                        for cheval in selection:
                            activite = {'type': 'Cours Passif', 'nom': cours['Coursautres_nom'], 'heure_debut': hd, 'heure_fin': hf}
                            schedule[cheval['nom']][jour].append(activite)
                            work_hours[cheval['nom']]['passive'] += duree
                    
                    for cheval_nom in liste_chevaux:
                        for jour in JOURS_SEMAINE:
                            schedule[cheval_nom][jour].sort(key=lambda x: x['heure_debut'])
                    
                    # Créer le rapport
                    report_data = []
                    for cheval_nom in liste_chevaux:
                        max_h = df_chevaux.loc[df_chevaux['Nom_Cheval'] == cheval_nom, 'Max_heures_Travail'].iloc[0]
                        heures_actives = work_hours[cheval_nom]['active']
                        depassement_val = round(heures_actives - max_h, 2) if max_h > 0 and heures_actives > max_h else 0
                        depassement_str = f"Oui ({depassement_val}h)" if depassement_val > 0 else "Non"
                        report_data.append({
                            "Nom du Cheval": cheval_nom, 
                            "Heures Actives": f"{heures_actives:.2f}", 
                            "Heures Passives": f"{work_hours[cheval_nom]['passive']:.2f}", 
                            "Heures Max": max_h, 
                            "Dépassement": depassement_str
                        })
                    
                    # Sauvegarder dans session state
                    st.session_state.schedule = schedule
                    st.session_state.df_report = pd.DataFrame(report_data)
                    st.session_state.horaires_generes = True
                    st.session_state.conflits = conflits
                    st.session_state.df_cours_manege_tries = df_cours_manege_tries
                    st.session_state.df_cours_autres_tries = df_cours_autres_tries
                    st.session_state.liste_chevaux = liste_chevaux
                    st.session_state.work_hours = work_hours
                    
                    progress_bar.progress(100)
                    status_text.text("✅ Génération terminée!")
                    st.success("🎉 Les horaires ont été générés avec succès!")
                    
                    # Afficher les conflits s'il y en a
                    if conflits:
                        st.warning(f"⚠️ {len(conflits)} conflits détectés. Consultez l'onglet Visualisation pour plus de détails.")
                    
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"❌ Erreur lors de la génération: {str(e)}")
                    st.exception(e)

# TAB 3: Visualisation améliorée
with tab3:
    if st.session_state.schedule is None:
        st.info("💡 Générez d'abord les horaires dans l'onglet 'Génération'")
    else:
        st.header("📊 Visualisation des horaires")
        
        # Afficher les conflits en premier s'il y en a
        if 'conflits' in st.session_state and st.session_state.conflits:
            with st.expander(f"⚠️ {len(st.session_state.conflits)} Conflits détectés", expanded=True):
                for conflit in st.session_state.conflits:
                    st.markdown(f'<div class="conflict-warning">⚠️ {conflit}</div>', unsafe_allow_html=True)
        
        # Sélecteur de type de vue uniquement
        col1, col2 = st.columns([3, 1])
        
        with col1:
            type_vue = st.selectbox(
                "Type de vue:",
                ["Vue complète", "Cours manège uniquement", "Mises en liberté uniquement", "Cours autres uniquement", "Par cheval", "Par jour"]
            )
        
        with col2:
            if st.button("🔄 Rafraîchir"):
                st.rerun()
        
        # Sélecteur de jour seulement si nécessaire
        if type_vue in ["Par jour", "Par cheval"]:
            jour_selectionne = st.selectbox(
                "Sélectionner un jour:",
                JOURS_SEMAINE
            )
        else:
            jour_selectionne = JOURS_SEMAINE[0]  # Premier jour par défaut pour les stats
        
        # Statistiques - maintenant pour la semaine complète
        st.markdown("### 📈 Statistiques de la semaine")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Calculer les stats pour toute la semaine
        nb_chevaux_total = len(st.session_state.schedule)
        total_cours_actifs = 0
        total_cours_passifs = 0
        total_libertes = 0
        
        for cheval, planning in st.session_state.schedule.items():
            for jour in JOURS_SEMAINE:
                if jour in planning:
                    for act in planning[jour]:
                        if act['type'] == 'Cours Actif':
                            total_cours_actifs += 1
                        elif act['type'] == 'Cours Passif':
                            total_cours_passifs += 1
                        elif act['type'] == 'Mise en liberté':
                            total_libertes += 1
        
        with col1:
            st.markdown(f"""
            <div class="stats-card">
                <div class="stats-number">{nb_chevaux_total}</div>
                <div>Chevaux total</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stats-card">
                <div class="stats-number">{total_cours_actifs}</div>
                <div>Cours actifs/semaine</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="stats-card">
                <div class="stats-number">{total_cours_passifs}</div>
                <div>Cours passifs/semaine</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="stats-card">
                <div class="stats-number">{total_libertes}</div>
                <div>Sorties/semaine</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Affichage selon le type de vue
        st.markdown("---")
        
        if type_vue == "Vue complète":
            # Vue hebdomadaire par type d'activité
            st.markdown("### 🏇 Horaire des cours de manège")
            manege_html = create_weekly_schedule_html(st.session_state.schedule, 'Cours Actif', JOURS_SEMAINE)
            st.markdown(manege_html, unsafe_allow_html=True)
            
            st.markdown("### 📚 Horaire des cours autres")
            autres_html = create_weekly_schedule_html(st.session_state.schedule, 'Cours Passif', JOURS_SEMAINE)
            st.markdown(autres_html, unsafe_allow_html=True)
            
            st.markdown("### 🏞️ Planning des mises en liberté")
            liberte_html = create_park_weekly_schedule_html(st.session_state.schedule, JOURS_SEMAINE)
        elif type_vue == "Cours autres uniquement":
            st.markdown(f"### 📚 Horaire des cours autres - Semaine complète")
            autres_html = create_weekly_schedule_html(st.session_state.schedule, 'Cours Passif', JOURS_SEMAINE)
            st.markdown(autres_html, unsafe_allow_html=True)
            
        elif type_vue == "Par jour":
            st.markdown(f"### 📅 Horaire complet - {jour_selectionne}")
            
            # Cours manège du jour
            st.markdown("#### 🏇 Cours de manège")
            manege_jour = create_weekly_schedule_html(st.session_state.schedule, 'Cours Actif', [jour_selectionne])
            st.markdown(manege_jour, unsafe_allow_html=True)
            
            # Cours autres du jour
            st.markdown("#### 📚 Cours autres")
            autres_jour = create_weekly_schedule_html(st.session_state.schedule, 'Cours Passif', [jour_selectionne])
            st.markdown(autres_jour, unsafe_allow_html=True)
            
            # Mises en liberté du jour
            st.markdown("#### 🏞️ Mises en liberté")
            liberte_jour = create_park_weekly_schedule_html(st.session_state.schedule, [jour_selectionne])
            st.markdown(liberte_jour, unsafe_allow_html=True)
            
        elif type_vue == "Cours manège uniquement":
            st.markdown(f"### 🏇 Horaire des cours de manège - Semaine complète")
            manege_html = create_weekly_schedule_html(st.session_state.schedule, 'Cours Actif', JOURS_SEMAINE)
            st.markdown(manege_html, unsafe_allow_html=True)
            
        elif type_vue == "Mises en liberté uniquement":
            st.markdown(f"### 🏞️ Planning des mises en liberté - Semaine complète")
            liberte_html = create_park_weekly_schedule_html(st.session_state.schedule, JOURS_SEMAINE)
            st.markdown(liberte_html, unsafe_allow_html=True)
            
        elif type_vue == "Par cheval":
            st.markdown("### 🐴 Vue par cheval")
            
            cheval_selectionne = st.selectbox(
                "Sélectionner un cheval:",
                sorted(st.session_state.schedule.keys())
            )
            
            if cheval_selectionne:
                # Afficher l'horaire de la semaine pour ce cheval
                st.markdown(f"#### Horaire de {cheval_selectionne}")
                
                # Informations sur la charge de travail
                if 'df_report' in st.session_state:
                    info_cheval = st.session_state.df_report[st.session_state.df_report['Nom du Cheval'] == cheval_selectionne]
                    if not info_cheval.empty:
                        info_cheval = info_cheval.iloc[0]
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.info(f"**Heures actives:** {info_cheval['Heures Actives']}")
                        with col2:
                            st.info(f"**Heures passives:** {info_cheval['Heures Passives']}")
                        with col3:
                            if "Oui" in str(info_cheval['Dépassement']):
                                st.error(f"**Dépassement:** {info_cheval['Dépassement']}")
                            else:
                                st.success(f"**Heures max:** {info_cheval['Heures Max']}h ✓")
                
                # Horaire de la semaine
                for jour in JOURS_SEMAINE:
                    activites = st.session_state.schedule[cheval_selectionne].get(jour, [])
                    if activites:
                        st.markdown(f"**{jour}:**")
                        for act in sorted(activites, key=lambda x: x['heure_debut']):
                            type_class = get_activity_style(act['type'])
                            st.markdown(f"""
                            <div class="course-block {type_class}" style="margin-left: 20px;">
                                {act['heure_debut'].strftime('%H:%M')} - {act['heure_fin'].strftime('%H:%M')} : 
                                <strong>{act['type']}</strong> - {act['nom']}
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"**{jour}:** _Journée libre_")

# TAB 4: Export amélioré
with tab4:
    if st.session_state.schedule is None:
        st.info("💡 Générez d'abord les horaires dans l'onglet 'Génération'")
    else:
        st.header("📥 Export des résultats")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📄 Export texte complet")
            if st.button("Générer le rapport texte", use_container_width=True):
                # Générer le rapport complet
                rapport = []
                rapport.append("="*70)
                rapport.append(f"HORAIRES ÉQUESTRES - Généré le {datetime.now().strftime('%Y-%m-%d à %H:%M:%S')}")
                rapport.append("="*70)
                rapport.append("")
                
                # RAPPORT 1: Horaires par cheval
                rapport.append("="*70)
                rapport.append("RAPPORT 1 : HORAIRE DÉTAILLÉ PAR CHEVAL")
                rapport.append("="*70)
                for cheval in sorted(st.session_state.schedule.keys()):
                    rapport.append(f"\nHoraires pour {cheval}:")
                    for jour in JOURS_SEMAINE:
                        activites = st.session_state.schedule[cheval][jour]
                        if activites:
                            rapport.append(f"  **{jour}**")
                            for act in activites:
                                rapport.append(f"    - {act['heure_debut'].strftime('%H:%M')}-{act['heure_fin'].strftime('%H:%M')} -> {act['type']}: {act['nom']}")
                        else:
                            rapport.append(f"  **{jour}**: Aucune activité planifiée.")
                
                # RAPPORT 2: Charge de travail
                rapport.append("\n" + "="*70)
                rapport.append("RAPPORT 2 : CHARGE DE TRAVAIL")
                rapport.append("="*70)
                rapport.append(st.session_state.df_report.to_string())
                
                # Conflits
                if st.session_state.conflits:
                    rapport.append("\n" + "="*70)
                    rapport.append("CONFLITS NON RÉSOLUS")
                    rapport.append("="*70)
                    for conflit in st.session_state.conflits:
                        rapport.append(f"- {conflit}")
                
                rapport_texte = "\n".join(rapport)
                
                # Bouton de téléchargement
                st.download_button(
                    label="📥 Télécharger le rapport texte",
                    data=rapport_texte,
                    file_name=f"horaires_equestres_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
                st.success("✅ Rapport texte prêt au téléchargement!")
        
        with col2:
            st.subheader("📊 Export Excel")
            if st.button("Générer le fichier Excel", use_container_width=True):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    # Feuille 1: Horaires complets
                    all_data = []
                    for cheval in sorted(st.session_state.schedule.keys()):
                        for jour in JOURS_SEMAINE:
                            for act in st.session_state.schedule[cheval][jour]:
                                all_data.append({
                                    'Cheval': cheval,
                                    'Jour': jour,
                                    'Début': act['heure_debut'].strftime('%H:%M'),
                                    'Fin': act['heure_fin'].strftime('%H:%M'),
                                    'Type': act['type'],
                                    'Activité': act['nom']
                                })
                    
                    if all_data:
                        pd.DataFrame(all_data).to_excel(writer, sheet_name='Horaires', index=False)
                    
                    # Feuille 2: Charge de travail
                    st.session_state.df_report.to_excel(writer, sheet_name='Charge de travail', index=False)
                    
                    # Feuille 3: Conflits
                    if st.session_state.conflits:
                        pd.DataFrame({'Conflits': st.session_state.conflits}).to_excel(writer, sheet_name='Conflits', index=False)
                
                st.download_button(
                    label="📥 Télécharger le fichier Excel",
                    data=output.getvalue(),
                    file_name=f"horaires_equestres_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.success("✅ Fichier Excel prêt au téléchargement!")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    🐴 Planificateur d'Horaires Équestres v2.0 | Interface visuelle améliorée
</div>
""", unsafe_allow_html=True)