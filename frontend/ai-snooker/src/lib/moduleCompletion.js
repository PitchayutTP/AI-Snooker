export function moduleCompletion(moduleId,data,catalog) {
  const exercises=catalog.filter(ex=>ex.module_id===moduleId);
  const results=exercises.map(ex=>data.find(row=>row.exercise_id===ex.id));
  const passed=results.filter(row=>row?.latest_assessment_status==='PASS');
  const consistent=passed.every(row=>row.completion_signature && row.completion_signature===passed[0]?.completion_signature);
  return {total:exercises.length,passed:passed.length,
    status:exercises.length && passed.length===exercises.length ? (consistent ? 'PASS' : 'DIFFERENT_SETTINGS') : 'INCOMPLETE'};
}
