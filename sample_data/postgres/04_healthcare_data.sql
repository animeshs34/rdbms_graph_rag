-- Healthcare Sample Data for PostgreSQL

-- Insert Patients
INSERT INTO patients (first_name, last_name, date_of_birth, gender, email, phone, address, city, state, zip_code, blood_type, allergies) VALUES
('Michael', 'Anderson', '1985-03-15', 'Male', 'michael.anderson@email.com', '555-1001', '100 Health St', 'Boston', 'MA', '02101', 'A+', 'Penicillin'),
('Sarah', 'Martinez', '1990-07-22', 'Female', 'sarah.martinez@email.com', '555-1002', '200 Wellness Ave', 'Boston', 'MA', '02102', 'O-', 'None'),
('David', 'Thompson', '1978-11-08', 'Male', 'david.thompson@email.com', '555-1003', '300 Care Blvd', 'Cambridge', 'MA', '02138', 'B+', 'Sulfa drugs'),
('Emily', 'Garcia', '1995-05-30', 'Female', 'emily.garcia@email.com', '555-1004', '400 Medical Ln', 'Boston', 'MA', '02103', 'AB+', 'None'),
('James', 'Rodriguez', '1982-09-12', 'Male', 'james.rodriguez@email.com', '555-1005', '500 Hospital Rd', 'Somerville', 'MA', '02143', 'O+', 'Latex'),
('Lisa', 'Lee', '1988-12-25', 'Female', 'lisa.lee@email.com', '555-1006', '600 Clinic Dr', 'Boston', 'MA', '02104', 'A-', 'None'),
('Robert', 'White', '1975-04-18', 'Male', 'robert.white@email.com', '555-1007', '700 Doctor Way', 'Cambridge', 'MA', '02139', 'B-', 'Aspirin'),
('Jennifer', 'Hall', '1992-08-05', 'Female', 'jennifer.hall@email.com', '555-1008', '800 Nurse St', 'Boston', 'MA', '02105', 'AB-', 'None'),
('William', 'Young', '1980-01-20', 'Male', 'william.young@email.com', '555-1009', '900 Patient Ave', 'Somerville', 'MA', '02144', 'O+', 'Peanuts'),
('Mary', 'King', '1987-06-14', 'Female', 'mary.king@email.com', '555-1010', '1000 Health Plaza', 'Boston', 'MA', '02106', 'A+', 'None');

-- Insert Doctors
INSERT INTO doctors (first_name, last_name, specialization, license_number, email, phone, years_of_experience, department) VALUES
('Dr. John', 'Smith', 'Cardiology', 'MD-12345', 'dr.smith@hospital.com', '555-2001', 15, 'Cardiology'),
('Dr. Emma', 'Johnson', 'Pediatrics', 'MD-12346', 'dr.johnson@hospital.com', '555-2002', 10, 'Pediatrics'),
('Dr. Michael', 'Brown', 'Orthopedics', 'MD-12347', 'dr.brown@hospital.com', '555-2003', 20, 'Orthopedics'),
('Dr. Sarah', 'Davis', 'Dermatology', 'MD-12348', 'dr.davis@hospital.com', '555-2004', 8, 'Dermatology'),
('Dr. Robert', 'Wilson', 'Neurology', 'MD-12349', 'dr.wilson@hospital.com', '555-2005', 12, 'Neurology'),
('Dr. Lisa', 'Moore', 'Internal Medicine', 'MD-12350', 'dr.moore@hospital.com', '555-2006', 18, 'Internal Medicine'),
('Dr. James', 'Taylor', 'Surgery', 'MD-12351', 'dr.taylor@hospital.com', '555-2007', 22, 'Surgery'),
('Dr. Patricia', 'Anderson', 'Psychiatry', 'MD-12352', 'dr.anderson@hospital.com', '555-2008', 14, 'Psychiatry');

-- Insert Appointments
INSERT INTO appointments (patient_id, doctor_id, appointment_date, duration_minutes, status, reason) VALUES
(1, 1, '2024-02-01 09:00:00', 30, 'completed', 'Annual checkup'),
(2, 2, '2024-02-01 10:00:00', 45, 'completed', 'Child vaccination'),
(3, 3, '2024-02-02 14:00:00', 60, 'completed', 'Knee pain'),
(4, 4, '2024-02-03 11:00:00', 30, 'completed', 'Skin rash'),
(5, 5, '2024-02-04 15:00:00', 45, 'completed', 'Headaches'),
(1, 1, '2024-02-05 09:30:00', 30, 'scheduled', 'Follow-up'),
(6, 6, '2024-02-06 10:00:00', 30, 'completed', 'Flu symptoms'),
(7, 7, '2024-02-07 13:00:00', 90, 'scheduled', 'Pre-surgery consultation'),
(8, 8, '2024-02-08 16:00:00', 60, 'completed', 'Anxiety'),
(9, 1, '2024-02-09 11:00:00', 30, 'completed', 'Chest pain'),
(10, 6, '2024-02-10 14:00:00', 30, 'scheduled', 'Diabetes management');

-- Insert Medications
INSERT INTO medications (name, generic_name, manufacturer, dosage_form, strength, description) VALUES
('Lisinopril', 'Lisinopril', 'PharmaCorp', 'Tablet', '10mg', 'ACE inhibitor for high blood pressure'),
('Metformin', 'Metformin HCl', 'MediPharm', 'Tablet', '500mg', 'Diabetes medication'),
('Amoxicillin', 'Amoxicillin', 'AntibioticCo', 'Capsule', '500mg', 'Antibiotic'),
('Ibuprofen', 'Ibuprofen', 'PainRelief Inc', 'Tablet', '200mg', 'Pain reliever and anti-inflammatory'),
('Atorvastatin', 'Atorvastatin', 'CholesterolMeds', 'Tablet', '20mg', 'Cholesterol-lowering medication'),
('Omeprazole', 'Omeprazole', 'GastroPharm', 'Capsule', '20mg', 'Proton pump inhibitor for acid reflux'),
('Sertraline', 'Sertraline HCl', 'MentalHealth Pharma', 'Tablet', '50mg', 'Antidepressant'),
('Albuterol', 'Albuterol Sulfate', 'RespiratoryCare', 'Inhaler', '90mcg', 'Bronchodilator for asthma');

-- Insert Diagnoses
INSERT INTO diagnoses (appointment_id, patient_id, doctor_id, diagnosis_code, diagnosis_name, description, severity, diagnosed_date) VALUES
(1, 1, 1, 'I10', 'Hypertension', 'Essential (primary) hypertension', 'Moderate', '2024-02-01'),
(3, 3, 3, 'M25.561', 'Knee Pain', 'Pain in right knee', 'Mild', '2024-02-02'),
(4, 4, 4, 'L30.9', 'Dermatitis', 'Unspecified dermatitis', 'Mild', '2024-02-03'),
(5, 5, 5, 'R51', 'Headache', 'Chronic tension headache', 'Moderate', '2024-02-04'),
(7, 6, 6, 'J11.1', 'Influenza', 'Flu with respiratory manifestations', 'Mild', '2024-02-06'),
(9, 8, 8, 'F41.1', 'Generalized Anxiety Disorder', 'GAD with panic attacks', 'Moderate', '2024-02-08'),
(10, 9, 1, 'I20.9', 'Angina Pectoris', 'Unspecified angina pectoris', 'Severe', '2024-02-09');

-- Insert Prescriptions
INSERT INTO prescriptions (patient_id, doctor_id, medication_id, diagnosis_id, dosage, frequency, duration_days, instructions, prescribed_date, refills_allowed) VALUES
(1, 1, 1, 1, '10mg', 'Once daily', 90, 'Take in the morning with food', '2024-02-01', 3),
(3, 3, 4, 2, '200mg', 'Three times daily', 14, 'Take with food', '2024-02-02', 0),
(4, 4, 3, 3, '500mg', 'Three times daily', 7, 'Complete full course', '2024-02-03', 0),
(5, 5, 4, 4, '200mg', 'As needed', 30, 'Do not exceed 6 tablets per day', '2024-02-04', 1),
(6, 6, 3, 5, '500mg', 'Three times daily', 10, 'Complete full course', '2024-02-06', 0),
(8, 8, 7, 6, '50mg', 'Once daily', 90, 'Take in the morning', '2024-02-08', 3),
(9, 1, 1, 7, '10mg', 'Once daily', 90, 'Take in the morning', '2024-02-09', 3),
(9, 1, 5, 7, '20mg', 'Once daily at bedtime', 90, 'Take at night', '2024-02-09', 3);

-- Insert Lab Tests
INSERT INTO lab_tests (patient_id, doctor_id, test_name, test_type, test_date, results, status) VALUES
(1, 1, 'Blood Pressure', 'Vital Signs', '2024-02-01', '145/92 mmHg', 'completed'),
(1, 1, 'Lipid Panel', 'Blood Test', '2024-02-01', 'Total Cholesterol: 220 mg/dL, LDL: 150 mg/dL', 'completed'),
(3, 3, 'X-Ray Knee', 'Imaging', '2024-02-02', 'Mild arthritis detected', 'completed'),
(5, 5, 'MRI Brain', 'Imaging', '2024-02-04', 'No abnormalities detected', 'completed'),
(6, 6, 'Flu Test', 'Rapid Test', '2024-02-06', 'Positive for Influenza A', 'completed'),
(9, 1, 'ECG', 'Cardiac Test', '2024-02-09', 'Abnormal - ST segment changes', 'completed'),
(9, 1, 'Troponin', 'Blood Test', '2024-02-09', 'Elevated levels', 'completed');

