// A single, fixed GEANT4 application: fire a beam into a slab of material and
// report the energy deposited in each depth bin as JSON. No user-supplied
// geometry, physics list or macro -- only the numbers below can vary, which is
// what keeps this safe to expose as a tool.
#include "G4RunManagerFactory.hh"
#include "G4NistManager.hh"
#include "G4Box.hh"
#include "G4LogicalVolume.hh"
#include "G4PVPlacement.hh"
#include "G4PVReplica.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4UserSteppingAction.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4Step.hh"
#include "G4SystemOfUnits.hh"
#include "G4UImanager.hh"
#include "QBBC.hh"
#include "G4VUserActionInitialization.hh"
#include <vector>
#include <iostream>
#include <iomanip>
#include <cstdlib>
#include <string>

namespace {
std::string gMaterial = "G4_WATER";
double gThicknessCm = 20.0;
int gBins = 20;
std::string gParticle = "proton";
double gEnergyMeV = 150.0;
int gEvents = 200;
std::vector<double> gEdep;          // MeV per bin
double gEdepTotal = 0.0;
}

class Detector : public G4VUserDetectorConstruction {
public:
  G4VPhysicalVolume* Construct() override {
    auto* nist = G4NistManager::Instance();
    auto* mat = nist->FindOrBuildMaterial(gMaterial);
    if (!mat) { std::cerr << "{\"error\":\"unknown material\"}" << std::endl; std::exit(2); }
    const double half = 0.5 * gThicknessCm * cm;
    const double side = 15.0 * cm;
    auto* worldMat = nist->FindOrBuildMaterial("G4_AIR");
    auto* worldBox = new G4Box("World", side, side, half + 5.0 * cm);
    auto* worldLog = new G4LogicalVolume(worldBox, worldMat, "World");
    auto* world = new G4PVPlacement(nullptr, {}, worldLog, "World", nullptr, false, 0);
    auto* targetBox = new G4Box("Target", side * 0.9, side * 0.9, half);
    auto* targetLog = new G4LogicalVolume(targetBox, mat, "Target");
    new G4PVPlacement(nullptr, {}, targetLog, "Target", worldLog, false, 0);
    auto* sliceBox = new G4Box("Slice", side * 0.9, side * 0.9, half / gBins);
    auto* sliceLog = new G4LogicalVolume(sliceBox, mat, "Slice");
    new G4PVReplica("Slice", sliceLog, targetLog, kZAxis, gBins, 2 * half / gBins);
    return world;
  }
};

class Gun : public G4VUserPrimaryGeneratorAction {
public:
  Gun() : fGun(new G4ParticleGun(1)) {
    auto* def = G4ParticleTable::GetParticleTable()->FindParticle(gParticle);
    if (!def) { std::cerr << "{\"error\":\"unknown particle\"}" << std::endl; std::exit(2); }
    fGun->SetParticleDefinition(def);
    fGun->SetParticleEnergy(gEnergyMeV * MeV);
    fGun->SetParticleMomentumDirection({0, 0, 1});
  }
  void GeneratePrimaries(G4Event* e) override {
    fGun->SetParticlePosition({0, 0, -0.5 * gThicknessCm * cm - 1.0 * cm});
    fGun->GeneratePrimaryVertex(e);
  }
private:
  G4ParticleGun* fGun;
};

class Stepping : public G4UserSteppingAction {
public:
  void UserSteppingAction(const G4Step* step) override {
    const double dep = step->GetTotalEnergyDeposit() / MeV;
    if (dep <= 0) return;
    const auto* touch = step->GetPreStepPoint()->GetTouchable();
    if (touch->GetVolume()->GetName() != "Slice") return;
    const int bin = touch->GetCopyNumber(0);
    if (bin >= 0 && bin < gBins) { gEdep[bin] += dep; gEdepTotal += dep; }
  }
};

class Actions : public G4VUserActionInitialization {
public:
  void Build() const override {
    SetUserAction(new Gun());
    SetUserAction(new Stepping());
  }
};

int main(int argc, char** argv) {
  for (int i = 1; i + 1 < argc; i += 2) {
    const std::string k = argv[i], v = argv[i + 1];
    if (k == "--material") gMaterial = v;
    else if (k == "--thickness-cm") gThicknessCm = std::atof(v.c_str());
    else if (k == "--bins") gBins = std::atoi(v.c_str());
    else if (k == "--particle") gParticle = v;
    else if (k == "--energy-mev") gEnergyMeV = std::atof(v.c_str());
    else if (k == "--events") gEvents = std::atoi(v.c_str());
  }
  gEdep.assign(gBins, 0.0);
  auto* rm = G4RunManagerFactory::CreateRunManager(G4RunManagerType::SerialOnly);
  rm->SetUserInitialization(new Detector());
  rm->SetUserInitialization(new QBBC);
  rm->SetUserInitialization(new Actions());
  rm->Initialize();
  G4UImanager::GetUIpointer()->ApplyCommand("/run/verbose 0");
  G4UImanager::GetUIpointer()->ApplyCommand("/event/verbose 0");
  G4UImanager::GetUIpointer()->ApplyCommand("/tracking/verbose 0");
  rm->BeamOn(gEvents);
  const double binCm = gThicknessCm / gBins;
  std::cout << std::fixed << std::setprecision(6);
  std::cout << "RESULT_JSON_START\n{\n";
  std::cout << "  \"material\": \"" << gMaterial << "\",\n";
  std::cout << "  \"particle\": \"" << gParticle << "\",\n";
  std::cout << "  \"energy_mev\": " << gEnergyMeV << ",\n";
  std::cout << "  \"events\": " << gEvents << ",\n";
  std::cout << "  \"thickness_cm\": " << gThicknessCm << ",\n";
  std::cout << "  \"bin_width_cm\": " << binCm << ",\n";
  std::cout << "  \"total_edep_mev\": " << gEdepTotal << ",\n";
  std::cout << "  \"edep_mev_per_bin\": [";
  for (int i = 0; i < gBins; ++i) std::cout << (i ? ", " : "") << gEdep[i];
  std::cout << "]\n}\nRESULT_JSON_END\n";
  delete rm;
  return 0;
}
