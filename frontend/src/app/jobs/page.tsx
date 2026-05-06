'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useApi } from '@/hooks/useApi';
import { jobsApi, JobCriteria } from '@/services/jobs';
import { skillsApi, Skill } from '@/services/skills';
import Layout from '@/components/Layout';
import { getErrorMessage } from '@/utils/errorHandler';

type SelectedSkill = {
  skill: Skill;
  weight: number;
};

export default function JobsPage() {
  const { data: criteriaList, loading: loadingCriteria, error: criteriaError, refetch: refetchCriteria } = useApi(() => jobsApi.getJobs(), []);
  const { data: skills, loading: loadingSkills } = useApi(() => skillsApi.getSkills(), []);

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [skillId, setSkillId] = useState(0);
  const [selectedSkills, setSelectedSkills] = useState<SelectedSkill[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const availableSkills = skills || [];
  const skillOptions = availableSkills.map((skill) => (
    <option key={skill.id} value={skill.id}>
      {skill.name} ({skill.category})
    </option>
  ));

  const selectedSkill = availableSkills.find((skill) => skill.id === skillId);

  const addSkill = () => {
    if (!selectedSkill) return;
    if (selectedSkills.some((item) => item.skill.id === selectedSkill.id)) {
      setMessage({ type: 'error', text: 'Cette compétence est déjà ajoutée.' });
      return;
    }
    setSelectedSkills([...selectedSkills, { skill: selectedSkill, weight: 50 }]);
    setMessage(null);
  };

  const removeSkill = (skillIdToRemove: number) => {
    setSelectedSkills(selectedSkills.filter((item) => item.skill.id !== skillIdToRemove));
  };

  const updateSkillWeight = (skillIdToUpdate: number, value: number) => {
    setSelectedSkills(selectedSkills.map((item) => item.skill.id === skillIdToUpdate ? { ...item, weight: value } : item));
  };

  const handleSubmit = async () => {
    if (!title.trim() || !description.trim()) {
      setMessage({ type: 'error', text: 'Le titre et la description sont obligatoires.' });
      return;
    }

    setSubmitting(true);
    setMessage(null);

    try {
      await jobsApi.createJob({
        title: title.trim(),
        description: description.trim(),
        criteria_skills: selectedSkills.map((item) => ({ skill_id: item.skill.id, weight: item.weight })),
      });

      setTitle('');
      setDescription('');
      setSkillId(0);
      setSelectedSkills([]);
      setMessage({ type: 'success', text: 'Critère créé avec succès.' });
      refetchCriteria();
    } catch (error: unknown) {
      setMessage({ type: 'error', text: getErrorMessage(error) });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Layout>
      <div>
        <div className="mb-8 flex items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Gestion des critères</h1>
            <p className="text-gray-600 mt-2">
              Créez, éditez et consultez vos critères de matching pour les candidats.
            </p>
          </div>
          <Link href="/matching" className="px-5 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
            Aller au matching
          </Link>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          <section className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Créer un nouveau critère</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Titre du critère</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Ex: Développeur Python senior"
                  className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={4}
                  placeholder="Décrivez le profil souhaité et les responsabilités"
                  className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Compétence à ajouter</label>
                  <select
                    value={skillId}
                    onChange={(e) => setSkillId(Number(e.target.value))}
                    className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-indigo-500 focus:outline-none"
                  >
                    <option value={0}>Sélectionner une compétence</option>
                    {skillOptions}
                  </select>
                </div>
                <button
                  type="button"
                  onClick={addSkill}
                  className="h-12 rounded-lg bg-indigo-600 text-white px-4 hover:bg-indigo-700"
                >
                  Ajouter
                </button>
              </div>

              {selectedSkills.length > 0 && (
                <div className="space-y-4">
                  <h3 className="text-sm font-medium text-gray-900">Compétences sélectionnées</h3>
                  {selectedSkills.map((item) => (
                    <div key={item.skill.id} className="rounded-lg border border-gray-200 p-4 bg-gray-50">
                      <div className="flex items-center justify-between gap-3 mb-3">
                        <div>
                          <p className="font-semibold text-gray-900">{item.skill.name}</p>
                          <p className="text-sm text-gray-500">{item.skill.category}</p>
                        </div>
                        <button
                          type="button"
                          onClick={() => removeSkill(item.skill.id)}
                          className="text-sm text-red-600 hover:text-red-800"
                        >
                          Supprimer
                        </button>
                      </div>
                      <div>
                        <label className="block text-sm text-gray-600 mb-2">Poids ({item.weight})</label>
                        <input
                          type="range"
                          min={0}
                          max={100}
                          value={item.weight}
                          onChange={(e) => updateSkillWeight(item.skill.id, Number(e.target.value))}
                          className="w-full"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {message && (
                <div className={`rounded-lg px-4 py-3 ${message.type === 'success' ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-700'}`}>
                  {message.text}
                </div>
              )}

              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="w-full rounded-lg bg-indigo-600 px-4 py-3 text-white hover:bg-indigo-700 disabled:opacity-60"
              >
                {submitting ? 'Création en cours...' : 'Créer le critère'}
              </button>
            </div>
          </section>

          <section className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Liste des critères</h2>
              <span className="text-sm text-gray-500">{criteriaList?.length ?? 0} critères</span>
            </div>

            {loadingCriteria && <p>Chargement des critères...</p>}
            {criteriaError && <p className="text-sm text-red-600">Erreur lors du chargement des critères.</p>}

            {!loadingCriteria && !criteriaList?.length && (
              <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center text-gray-500">
                Aucun critère trouvé. Créez le premier critère ci-contre.
              </div>
            )}

            <div className="space-y-4">
              {criteriaList?.map((criteria) => (
                <div key={criteria.id} className="rounded-lg border border-gray-200 p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="font-semibold text-gray-900">{criteria.title}</p>
                      <p className="text-sm text-gray-500">{criteria.description}</p>
                    </div>
                    <Link
                      href={`/matching`}
                      className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
                    >
                      Utiliser
                    </Link>
                  </div>
                  <div className="mt-3 text-sm text-gray-500">
                    Skills: {criteria.criteria_skills?.map((skill) => skill.skill_id).join(', ') || 'Aucune compétence'}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </Layout>
  );
}
