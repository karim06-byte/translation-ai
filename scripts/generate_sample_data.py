"""Generate additional sample training data."""
import json
import os
from pathlib import Path

# Sample English-Azerbaijani translation pairs
sample_pairs = [
    ("The cat sat on the mat.", "Pişik xalça üzərində oturdu."),
    ("She loves reading books in the evening.", "O, axşam kitab oxumağı sevir."),
    ("The weather is beautiful today.", "Bu gün hava gözəldir."),
    ("They went to the market to buy vegetables.", "Onlar tərəvəz almaq üçün bazara getdilər."),
    ("Education is very important for children.", "Təhsil uşaqlar üçün çox vacibdir."),
    ("The mountain was covered with snow.", "Dağ qarla örtülmüşdü."),
    ("He works as a teacher at the school.", "O, məktəbdə müəllim kimi işləyir."),
    ("The river flows into the sea.", "Çay dənizə axır."),
    ("We should protect our environment.", "Biz ətraf mühitimizi qorumalıyıq."),
    ("The library opens at nine o'clock.", "Kitabxana saat doqquzda açılır."),
    ("She wrote a letter to her friend.", "O, dostuna məktub yazdı."),
    ("The sun sets in the west.", "Günəş qərbdə batır."),
    ("They are learning a new language.", "Onlar yeni dil öyrənirlər."),
    ("The garden is full of beautiful flowers.", "Bağ gözəl çiçəklərlə doludur."),
    ("He plays the piano very well.", "O, pianinonu çox yaxşı çalır."),
    ("The meeting will start at three o'clock.", "Görüş saat üçdə başlayacaq."),
    ("She bought a new dress for the party.", "O, tədbir üçün yeni paltar aldı."),
    ("The students are studying for their exams.", "Tələbələr imtahanları üçün oxuyurlar."),
    ("The bird flew high in the sky.", "Quş səmada yüksək uçdu."),
    ("We need to save water for future generations.", "Biz gələcək nəsillər üçün su qorumalıyıq."),
    ("The museum displays ancient artifacts.", "Muzey qədim artefaktları nümayiş etdirir."),
    ("He enjoys playing football with his friends.", "O, dostları ilə futbol oynamağı sevir."),
    ("The train arrived at the station on time.", "Qatar vaxtında stansiyaya çatdı."),
    ("She is preparing dinner for her family.", "O, ailəsi üçün şam yeməyi hazırlayır."),
    ("The forest is home to many animals.", "Meşə bir çox heyvanların evidir."),
    ("They visited the historical monument yesterday.", "Onlar dünən tarixi abidəni ziyarət etdilər."),
    ("The computer helps us work more efficiently.", "Kompüter bizə daha səmərəli işləməyə kömək edir."),
    ("The doctor examined the patient carefully.", "Həkim xəstəni diqqətlə yoxladı."),
    ("The book tells an interesting story.", "Kitab maraqlı bir hekayə danışır."),
    ("We should respect our elders.", "Biz böyüklərimizə hörmət etməliyik."),
    ("The ocean is vast and mysterious.", "Okean geniş və sirrlidir."),
    ("She practices yoga every morning.", "O, hər səhər yoga məşq edir."),
    ("The city has many beautiful parks.", "Şəhərdə çoxlu gözəl parklar var."),
    ("He is reading a newspaper in the cafe.", "O, kafedə qəzet oxuyur."),
    ("The stars shine brightly in the night sky.", "Ulduzlar gecə səmasında parlaq parıldayır."),
    ("They are planning a trip to the mountains.", "Onlar dağlara səfər planlaşdırırlar."),
    ("The teacher explained the lesson clearly.", "Müəllim dərsi aydın izah etdi."),
    ("The bridge connects the two sides of the river.", "Körpü çayın iki tərəfini birləşdirir."),
    ("She is learning to play the guitar.", "O, gitara çalmağı öyrənir."),
    ("The festival celebrates local culture.", "Festival yerli mədəniyyəti qeyd edir."),
    ("We must take care of our health.", "Biz sağlamlığımıza qayğı göstərməliyik."),
    ("The painting shows a beautiful landscape.", "Rəsm gözəl bir mənzərə göstərir."),
    ("He writes poetry in his spare time.", "O, boş vaxtında şeir yazır."),
    ("The market is busy on weekends.", "Bazar həftə sonları məşğuldur."),
    ("They are building a new hospital.", "Onlar yeni xəstəxana tikirlər."),
    ("The moon appears in the evening sky.", "Ay axşam səmasında görünür."),
    ("She teaches mathematics at the university.", "O, universitetdə riyaziyyat öyrədir."),
    ("The road leads to the ancient castle.", "Yol qədim qalaya aparır."),
    ("We should appreciate what we have.", "Biz nəyə sahib olduğumuzu qiymətləndirməliyik."),
    ("The concert was attended by many people.", "Konsertə çoxlu insan qatıldı."),
]


def generate_jsonl(output_path: str, pairs: list):
    """Generate JSONL file from translation pairs."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for idx, (en, az) in enumerate(pairs):
            entry = {
                "id": f"sample_{idx:04d}",
                "en": en,
                "az": az
            }
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"Generated {len(pairs)} translation pairs in {output_path}")


def main():
    # Create data directories
    data_dir = Path("data")
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"
    
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate JSONL directly for quick training
    jsonl_path = processed_dir / "sample_data.jsonl"
    generate_jsonl(str(jsonl_path), sample_pairs)
    
    # Also create train/val/test splits
    import random
    random.seed(42)
    shuffled = sample_pairs.copy()
    random.shuffle(shuffled)
    
    train_end = int(len(shuffled) * 0.8)
    val_end = train_end + int(len(shuffled) * 0.1)
    
    train_pairs = shuffled[:train_end]
    val_pairs = shuffled[train_end:val_end]
    test_pairs = shuffled[val_end:]
    
    generate_jsonl(str(processed_dir / "sample_train.jsonl"), train_pairs)
    generate_jsonl(str(processed_dir / "sample_val.jsonl"), val_pairs)
    generate_jsonl(str(processed_dir / "sample_test.jsonl"), test_pairs)
    
    print(f"\nGenerated training data:")
    print(f"  Train: {len(train_pairs)} pairs")
    print(f"  Val: {len(val_pairs)} pairs")
    print(f"  Test: {len(test_pairs)} pairs")
    print(f"\nFiles created in: {processed_dir}")


if __name__ == "__main__":
    main()

