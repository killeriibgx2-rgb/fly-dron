package com.zzynes.flydrone.Domm;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.world.MenuProvider;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.inventory.ContainerData;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraftforge.items.ItemStackHandler;
import org.jetbrains.annotations.Nullable;

public class DommBlockEntity extends BlockEntity implements MenuProvider {
    private int coalStored = 0;
    private float temperature = 0.0f;
    private boolean isFormed = false;
    private float coalConsumption = 0.0f;
    private int tickCounter = 0;

    public final ItemStackHandler itemHandler = new ItemStackHandler(4) {
        @Override
        protected void onContentsChanged(int slot) {
            setChanged();
            if (slot == 0) {
                processFuelSlot();
            }
        }
    };

    protected final ContainerData dataAccess = new ContainerData() {
        @Override
        public int get(int index) {
            return switch (index) {
                case 0 -> coalStored;
                case 1 -> (int) temperature;
                default -> 0;
            };
        }

        @Override
        public void set(int index, int value) {
            switch (index) {
                case 0 -> coalStored = value;
                case 1 -> temperature = value;
            }
        }

        @Override
        public int getCount() {
            return 2;
        }
    };

    public DommBlockEntity(BlockPos pos, BlockState state) {
        super(DommRegistry.DOMM_BLOCK_ENTITY.get(), pos, state);
    }

    private void processFuelSlot() {
        if (this.level == null || this.level.isClientSide()) return;
        ItemStack fuelStack = itemHandler.getStackInSlot(0);
        if (fuelStack.isEmpty()) return;

        if (fuelStack.is(Items.COAL)) {
            int count = fuelStack.getCount();
            int space = 64 - coalStored;
            int toAdd = Math.min(count, space);
            if (toAdd > 0) {
                coalStored += toAdd;
                fuelStack.shrink(toAdd);
                if (fuelStack.isEmpty()) {
                    itemHandler.setStackInSlot(0, ItemStack.EMPTY);
                }
                setChanged();
            }
        }
    }

    public static void tick(Level level, BlockPos pos, BlockState state, DommBlockEntity entity) {
        if (level.isClientSide()) return;

        entity.tickCounter++;
        if (entity.tickCounter >= 20) {
            entity.tickCounter = 0;
            boolean formed = entity.checkMultiblock();
            if (formed != entity.isFormed) {
                entity.setFormed(formed);
            }
        }

        if (entity.coalStored > 0 && entity.isFormed) {
            if (entity.temperature < 2000.0f) {
                entity.temperature += 0.3333f;
                if (entity.temperature > 2000.0f) entity.temperature = 2000.0f;
                entity.coalConsumption += 0.0033f;
                if (entity.coalConsumption >= 1.0f) {
                    entity.coalStored--;
                    entity.coalConsumption -= 1.0f;
                }
                entity.setChanged();
            } else {
                entity.coalConsumption += 0.0033f;
                if (entity.coalConsumption >= 1.0f) {
                    entity.coalStored--;
                    entity.coalConsumption -= 1.0f;
                }
                entity.setChanged();
            }
        } else {
            if (entity.temperature > 0.0f) {
                entity.temperature -= 0.3333f;
                if (entity.temperature < 0.0f) entity.temperature = 0.0f;
                entity.setChanged();
            }
        }
    }

    private boolean checkMultiblock() {
        if (this.level == null) return false;
        BlockState interfaceState = this.level.getBlockState(this.worldPosition);
        if (!interfaceState.hasProperty(DommInterfaceBlock.FACING)) return false;

        Direction front = interfaceState.getValue(DommInterfaceBlock.FACING);

        for (int ly = -1; ly <= 3; ly++) {
            for (int lx = -1; lx <= 1; lx++) {
                for (int lz = 0; lz <= 2; lz++) {
                    if (lx == 0 && ly == 0 && lz == 0) continue;

                    BlockPos checkPos = getRelativePos(this.worldPosition, front, lx, ly, lz);
                    BlockState state = this.level.getBlockState(checkPos);

                    boolean shouldBeAir = (ly == 3 && !(lx == 0 && lz == 1));

                    if (shouldBeAir) {
                        if (!state.isAir()) return false;
                    } else {
                        if (!state.is(DommRegistry.DOMM_BODY.get())) return false;
                    }
                }
            }
        }
        return true;
    }

    private static BlockPos getRelativePos(BlockPos center, Direction front, int lx, int ly, int lz) {
        BlockPos pos = center;
        if (lx == -1) pos = pos.relative(front.getCounterClockWise());
        else if (lx == 1) pos = pos.relative(front.getClockWise());

        if (ly < 0) pos = pos.below(-ly);
        else if (ly > 0) pos = pos.above(ly);

        if (lz == 1) pos = pos.relative(front.getOpposite());
        else if (lz == 2) pos = pos.relative(front.getOpposite()).relative(front.getOpposite());

        return pos;
    }

    public int addCoal(int amount) {
        int space = 64 - this.coalStored;
        int added = Math.min(space, amount);
        this.coalStored += added;
        this.setChanged();
        return added;
    }

    @Override
    protected void saveAdditional(CompoundTag tag) {
        super.saveAdditional(tag);
        tag.putInt("coalStored", coalStored);
        tag.putFloat("temperature", temperature);
        tag.putBoolean("isFormed", isFormed);
        tag.putFloat("coalConsumption", coalConsumption);
        tag.put("inventory", itemHandler.serializeNBT());
    }

    @Override
    public void load(CompoundTag tag) {
        super.load(tag);
        coalStored = tag.getInt("coalStored");
        temperature = tag.getFloat("temperature");
        isFormed = tag.getBoolean("isFormed");
        coalConsumption = tag.getFloat("coalConsumption");
        itemHandler.deserializeNBT(tag.getCompound("inventory"));
    }

    public int getCoalStored() {
        return coalStored;
    }

    public float getTemperature() {
        return temperature;
    }

    public boolean isFormed() {
        return isFormed;
    }

    public void setFormed(boolean formed) {
        this.isFormed = formed;
        this.setChanged();
    }

    @Override
    public Component getDisplayName() {
        return Component.literal("Доменная печь");
    }

    @Nullable
    @Override
    public AbstractContainerMenu createMenu(int containerId, Inventory playerInventory, Player player) {
        return new DommMenu(containerId, playerInventory, this, this.dataAccess);
    }
}